from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _db_path() -> Path:
    return Path(os.getenv("SQLITE_DB_PATH", "meeting_agent.db"))


# Kept as a module variable so tests can monkeypatch it.
DB_PATH = _db_path()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                owner TEXT,
                deadline TEXT,
                priority TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                source_meeting TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
