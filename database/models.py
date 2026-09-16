from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: int | None
    task: str
    owner: str | None
    deadline: str | None
    priority: str | None
    status: str
    source_meeting: str | None
    created_at: str
