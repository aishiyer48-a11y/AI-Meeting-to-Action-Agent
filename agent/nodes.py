from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from langgraph.types import interrupt

from database.crud import create_task
from llm.client import analyze_transcript, get_client
from llm.schemas import ActionItem, ActionType, MeetingAnalysis, ProposedCalendarEvent
from tools.calendar_tool import create_calendar_event


def _analysis(state) -> MeetingAnalysis:
    return MeetingAnalysis.model_validate(state["analysis"])


def analyze_node(state):
    reference_date = datetime.now().date().isoformat()
    analysis = analyze_transcript(state["transcript"], reference_date)
    return {
        "analysis": analysis.model_dump(mode="json"),
        "action_index": 0,
        "status": "ANALYZED",
        "last_result": None,
        "approval": None,
        "current_missing": [],
    }


def route_action(state):
    analysis = _analysis(state)
    actions = analysis.action_items
    idx = state.get("action_index", 0)

    if idx >= len(actions):
        return "finish"

    action = actions[idx]
    if action.action_type == ActionType.NORMAL_TASK:
        return "task"
    # Both meeting requests and incomplete meeting requests must pass
    # through validation so missing information is calculated from the
    # structured fields rather than relying on the LLM wording.
    if action.action_type in {ActionType.SCHEDULE_MEETING, ActionType.CLARIFICATION_REQUIRED}:
        return "meeting"
    return "meeting"


def save_task_node(state):
    analysis = _analysis(state)
    action = analysis.action_items[state["action_index"]]

    if not action.task:
        return {
            "status": "TASK_SKIPPED",
            "last_result": {
                "type": "error",
                "message": "Task text was missing.",
            },
            "action_index": state["action_index"] + 1,
        }

    try:
        task_id = create_task(
            task=action.task,
            owner=action.owner,
            deadline=action.deadline,
            priority=action.priority,
            source_meeting=state["transcript"],
        )
    except Exception as exc:
        return {
            "status": "TASK_FAILED",
            "last_result": {
                "type": "error",
                "message": f"SQLite error: {exc}",
            },
            "action_index": state["action_index"] + 1,
        }

    return {
        "status": "TASK_CREATED",
        "last_result": {
            "type": "task",
            "task_id": task_id,
            "message": f"Task #{task_id} saved to SQLite.",
        },
        "action_index": state["action_index"] + 1,
    }


def _parse_meeting_time(time_text: str) -> datetime:
    text = str(time_text).strip()
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Unsupported meeting time format: '{time_text}'. "
        "Expected formats such as '3:00 PM' or '15:00'."
    )


def _missing_meeting_information(action: ActionItem) -> list[str]:
    missing: list[str] = []

    if not action.date:
        missing.append("date")
    if not action.start_time:
        missing.append("start time")
    if not action.end_time and not action.duration_minutes:
        missing.append("end time/duration")

    # Preserve any useful structured missing fields supplied by the model,
    # while removing duplicates and generic placeholders.
    for item in action.missing_information:
        item = str(item).strip()
        if item and item.lower() not in {"required information", "missing information"} and item not in missing:
            missing.append(item)
    return missing


def validate_meeting_node(state):
    analysis = _analysis(state)
    action = analysis.action_items[state["action_index"]]
    missing = _missing_meeting_information(action)

    if missing:
        return {
            "current_action": action.model_dump(mode="json"),
            "current_missing": missing,
            "status": "CLARIFICATION_REQUIRED",
        }

    try:
        parsed_start = _parse_meeting_time(action.start_time)
        if action.end_time:
            parsed_end = _parse_meeting_time(action.end_time)
        else:
            parsed_end = parsed_start + timedelta(minutes=action.duration_minutes or 0)
    except ValueError as exc:
        return {
            "current_action": action.model_dump(mode="json"),
            "current_missing": ["valid meeting time (for example, 3:00 PM)"],
            "status": "CLARIFICATION_REQUIRED",
            "last_result": {"type": "error", "message": str(exc)},
        }

    if parsed_end <= parsed_start:
        return {
            "current_action": action.model_dump(mode="json"),
            "current_missing": ["an end time later than the start time"],
            "status": "CLARIFICATION_REQUIRED",
        }

    event = ProposedCalendarEvent(
        title=action.title or action.purpose or "Meeting",
        date=action.date,
        start_time=parsed_start.strftime("%H:%M"),
        end_time=parsed_end.strftime("%H:%M"),
        participants=action.participants,
        purpose=action.purpose or "",
    )

    return {
        "proposed_event": event.model_dump(mode="json"),
        "current_missing": [],
        "status": "AWAITING_APPROVAL",
    }


def clarification_node(state):
    missing = state.get("current_missing") or ["required meeting information"]
    prompt = (
        "I need the following information before I can prepare the calendar action: "
        + ", ".join(missing)
        + ". Please provide the missing details."
    )

    answer = interrupt({
        "type": "clarification",
        "prompt": prompt,
        "missing": missing,
    })

    return {
        "clarification_answer": str(answer),
        "status": "CLARIFICATION_RECEIVED",
    }


def apply_clarification_node(state):
    analysis = _analysis(state)
    action = analysis.action_items[state["action_index"]]
    client = get_client()

    import os
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Update the pending meeting action using ONLY the user's clarification. "
                    "Do not invent facts. Preserve all already-known fields. "
                    "Return one ActionItem. Keep action_type as SCHEDULE_MEETING."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pending action: {action.model_dump_json()}\n"
                    f"User clarification: {state['clarification_answer']}"
                ),
            },
        ],
        text_format=ActionItem,
    )

    updated = response.output_parsed
    if updated is None:
        raise RuntimeError("The LLM returned no structured clarification result.")
    updated.action_type = ActionType.SCHEDULE_MEETING
    analysis.action_items[state["action_index"]] = updated

    return {
        "analysis": analysis.model_dump(mode="json"),
        "status": "CLARIFICATION_APPLIED",
    }


def approval_node(state):
    event = state["proposed_event"]
    decision = interrupt({
        "type": "approval",
        "message": "Approve this calendar event?",
        "event": event,
    })
    decision = str(decision).upper().strip()
    if decision not in {"APPROVE", "REJECT"}:
        raise ValueError("Approval must be APPROVE or REJECT.")
    return {"approval": decision, "status": f"{decision}ED"}


def calendar_execute_node(state):
    event = state["proposed_event"]

    if state.get("approval") != "APPROVE":
        return {
            "last_result": {
                "type": "rejected",
                "message": "Calendar action rejected; no Calendar API call was made.",
            },
            "action_index": state["action_index"] + 1,
            "status": "REJECTED",
        }

    try:
        result = create_calendar_event(
            title=event["title"],
            date=event["date"],
            start_time=event["start_time"],
            end_time=event["end_time"],
            attendees=event.get("participants", []),
            description=event.get("purpose", ""),
            timezone=event.get("timezone", "Asia/Kolkata"),
        )
    except Exception as exc:
        return {
            "last_result": {"type": "error", "message": f"Calendar error: {exc}"},
            "action_index": state["action_index"] + 1,
            "status": "CALENDAR_FAILED",
        }

    result_data = {
        "type": "calendar",
        "message": "Google Calendar event created.",
        "event_id": result.get("id"),
        "html_link": result.get("htmlLink"),
    }
    if result.get("mock"):
        result_data["mock"] = True

    return {
        "last_result": result_data,
        "action_index": state["action_index"] + 1,
        "status": "CALENDAR_CREATED",
    }
