"""Calendar scheduling and natural relative date parsing."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional
from jarvis.core.logger import get_logger
from jarvis.memory.semantic_store import semantic_store

logger = get_logger("JARVIS.Calendar")


def parse_natural_datetime(text: str) -> Optional[datetime]:
    """Parse relative time expressions like 'in 15 minutes', 'tomorrow', 'in 2 hours'."""
    now = datetime.now(timezone.utc)
    t = text.lower().strip()

    # Match: "in X minutes" / "in X mins"
    m_min = re.search(r"in\s+(\d+)\s*(?:minutes|mins|m)\b", t)
    if m_min:
        return now + timedelta(minutes=int(m_min.group(1)))

    # Match: "in X hours" / "in X hrs"
    m_hr = re.search(r"in\s+(\d+)\s*(?:hours|hrs|h)\b", t)
    if m_hr:
        return now + timedelta(hours=int(m_hr.group(1)))

    # Match: "in X days"
    m_day = re.search(r"in\s+(\d+)\s*(?:days|d)\b", t)
    if m_day:
        return now + timedelta(days=int(m_day.group(1)))

    # Match: "tomorrow"
    if "tomorrow" in t:
        tomorrow = now + timedelta(days=1)
        # Check if time specified (e.g. at 5pm)
        m_time = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", t)
        if m_time:
            hour = int(m_time.group(1))
            minute = int(m_time.group(2) or 0)
            meridiem = m_time.group(3)
            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

    return None


class CalendarManager:
    """Manages reminders and scheduled calendar events with natural language time parsing."""

    def schedule_reminder(
        self,
        title: str,
        time_expression: str,
        description: str = "",
        recurrence: str = "none",
    ) -> Dict[str, Any]:
        """Schedule a reminder using relative or natural time expression."""
        due_at = parse_natural_datetime(time_expression)
        if not due_at:
            # Fallback default: 1 hour from now
            due_at = datetime.now(timezone.utc) + timedelta(hours=1)
            logger.info(f"Could not parse '{time_expression}'. Defaulting reminder to 1 hour from now.")

        reminder = semantic_store.add_reminder(
            title=title,
            due_at=due_at,
            description=description,
            recurrence=recurrence,
        )
        logger.info(f"Scheduled reminder: '{title}' due at {due_at.isoformat()}")
        return {
            "success": True,
            "id": reminder["id"],
            "title": title,
            "due_at": due_at.isoformat(),
            "message": f"Reminder scheduled for '{title}' at {due_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        }

    def list_due_reminders(self) -> List[Dict[str, Any]]:
        """Find pending reminders whose due time has elapsed."""
        pending = semantic_store.get_pending_reminders()
        now = datetime.now(timezone.utc)
        due_now = []
        for r in pending:
            due_dt = datetime.fromisoformat(r["due_at"])
            if due_dt <= now:
                due_now.append(r)
        return due_now

    def mark_completed(self, reminder_id: str) -> bool:
        """Mark reminder as completed."""
        return semantic_store.mark_reminder_completed(reminder_id)


# Singleton calendar manager
calendar_manager = CalendarManager()
