from __future__ import annotations

from datetime import datetime
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import get_credentials


def _parse_calendar_datetime(date: str, time: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %I %p"):
        try:
            return datetime.strptime(f"{date} {str(time).strip()}", fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid calendar date/time: {date} {time}")


def create_calendar_event(title: str, date: str, start_time: str, end_time: str, attendees: list[str], description: str, timezone: str = "Asia/Kolkata") -> dict:
    """Create a real Google Calendar event. Call this only after explicit approval."""
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        return {"id": "DEMO-EVENT", "htmlLink": None, "mock": True}

    start = _parse_calendar_datetime(date, start_time)
    end = _parse_calendar_datetime(date, end_time)
    if end <= start:
        raise ValueError("Calendar end time must be later than start time.")

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": timezone},
    }

    clean_attendees = [a.strip() for a in attendees if a and "@" in a]
    if clean_attendees:
        body["attendees"] = [{"email": email} for email in clean_attendees]

    try:
        return service.events().insert(calendarId="primary", body=body, sendUpdates="all").execute()
    except HttpError as exc:
        raise RuntimeError(f"Google Calendar API error: {exc}") from exc
