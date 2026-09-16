from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    transcript: str
    analysis: dict[str, Any]
    action_index: int
    status: str
    current_action: dict[str, Any]
    current_missing: list[str]
    proposed_event: dict[str, Any]
    last_result: dict[str, Any]
    clarification_answer: str
    approval: str
    errors: list[str]
