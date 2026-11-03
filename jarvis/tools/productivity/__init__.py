"""Productivity automation tools (Notes, Calendar, Email, WhatsApp)."""

from jarvis.tools.productivity.calendar_manager import (
    CalendarManager,
    calendar_manager,
    parse_natural_datetime,
)
from jarvis.tools.productivity.email_client import EmailClient, email_client
from jarvis.tools.productivity.whatsapp_client import WhatsAppClient, whatsapp_client

__all__ = [
    "CalendarManager",
    "calendar_manager",
    "parse_natural_datetime",
    "EmailClient",
    "email_client",
    "WhatsAppClient",
    "whatsapp_client",
]
