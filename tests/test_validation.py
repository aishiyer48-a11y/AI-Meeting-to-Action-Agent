from agent.nodes import validate_meeting_node
from llm.schemas import ActionItem, ActionType, MeetingAnalysis


def test_missing_meeting_time():
    state = {
        "analysis": MeetingAnalysis(meeting_summary="x", action_items=[ActionItem(action_type=ActionType.SCHEDULE_MEETING, date="2026-09-16")]),
        "action_index": 0,
    }
    out = validate_meeting_node(state)
    assert out["status"] == "CLARIFICATION_REQUIRED"
    assert "start time" in out["current_missing"]
