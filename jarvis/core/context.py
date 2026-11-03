"""Runtime system context and environment awareness for JARVIS."""

from __future__ import annotations
import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class SystemContext:
    """Snapshot of current machine and environment state."""
    os_name: str = field(default_factory=lambda: f"Windows {platform.release()} ({platform.version()})")
    python_version: str = field(default_factory=lambda: platform.python_version())
    machine_architecture: str = field(default_factory=lambda: platform.machine())
    hostname: str = field(default_factory=lambda: os.environ.get("COMPUTERNAME", "localhost"))
    username: str = field(default_factory=lambda: os.getenv("USERNAME", "User"))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Dynamic system states
    active_window_title: str = ""
    active_process_name: str = ""
    battery_percent: float | None = None
    is_battery_charging: bool | None = None
    cpu_percent: float | None = None
    memory_percent: float | None = None

    # Dynamic assistant states
    current_session_id: str = "default_session"
    is_listening: bool = False
    is_speaking: bool = False
    is_thinking: bool = False
    last_user_query: str = ""
    last_assistant_response: str = ""
    clipboard_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert system context to dictionary for LLM prompt injection."""
        return {
            "os": self.os_name,
            "user": self.username,
            "host": self.hostname,
            "python": self.python_version,
            "active_window": self.active_window_title or "None (Desktop)",
            "battery": f"{self.battery_percent:.0f}%" if self.battery_percent is not None else "Unknown",
            "cpu_usage": f"{self.cpu_percent:.1f}%" if self.cpu_percent is not None else "Unknown",
            "memory_usage": f"{self.memory_percent:.1f}%" if self.memory_percent is not None else "Unknown",
            "session_id": self.current_session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global singleton context
runtime_context = SystemContext()
