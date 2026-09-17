from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    NORMAL_TASK = "NORMAL_TASK"
    SCHEDULE_MEETING = "SCHEDULE_MEETING"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"


class ActionItem(BaseModel):
    action_type: ActionType
    task: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None
    participants: list[str] = Field(default_factory=list)
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    purpose: Optional[str] = None
    missing_information: list[str] = Field(default_factory=list)


class MeetingAnalysis(BaseModel):
    meeting_summary: str
    key_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)


class ProposedCalendarEvent(BaseModel):
    title: str
    date: str
    start_time: str
    end_time: str
    participants: list[str] = Field(default_factory=list)
    purpose: str = ""
    timezone: str = "Asia/Kolkata"
