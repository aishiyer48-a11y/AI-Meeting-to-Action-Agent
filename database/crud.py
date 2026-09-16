from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import get_connection, init_db


def create_task(task: str, owner: str | None = None, deadline: str | None = None,
                priority: str | None = None, source_meeting: str | None = None) -> int:
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tasks(task, owner, deadline, priority, status, source_meeting, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task, owner, deadline, priority, "Pending", source_meeting, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_task(task_id: int) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def get_all_tasks() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def update_task(task_id: int, **fields: Any) -> bool:
    init_db()
    allowed = {"task", "owner", "deadline", "priority", "status", "source_meeting"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", [*updates.values(), task_id])
        conn.commit()
        return cur.rowcount > 0


def delete_task(task_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0
