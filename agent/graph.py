from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import (
    analyze_node, approval_node, apply_clarification_node, calendar_execute_node,
    clarification_node, route_action, save_task_node, validate_meeting_node,
)
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("analyze", analyze_node)
    graph.add_node("save_task", save_task_node)
    graph.add_node("validate_meeting", validate_meeting_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("apply_clarification", apply_clarification_node)
    graph.add_node("approval", approval_node)
    graph.add_node("calendar_execute", calendar_execute_node)

    graph.add_edge(START, "analyze")
    graph.add_conditional_edges("analyze", route_action, {
        "task": "save_task",
        "meeting": "validate_meeting",
        "finish": END,
    })
    graph.add_conditional_edges("save_task", route_action, {
        "task": "save_task",
        "meeting": "validate_meeting",
        "finish": END,
    })
    graph.add_conditional_edges(
        "validate_meeting",
        lambda s: "clarification" if s.get("status") == "CLARIFICATION_REQUIRED" else "approval",
        {"clarification": "clarification", "approval": "approval"},
    )
    graph.add_edge("clarification", "apply_clarification")
    graph.add_edge("apply_clarification", "validate_meeting")
    graph.add_edge("approval", "calendar_execute")
    graph.add_conditional_edges("calendar_execute", route_action, {
        "task": "save_task",
        "meeting": "validate_meeting",
        "finish": END,
    })

    return graph.compile(checkpointer=InMemorySaver())
