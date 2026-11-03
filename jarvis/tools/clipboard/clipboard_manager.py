"""Clipboard monitoring, history tracking, and automation."""

from __future__ import annotations
from datetime import datetime, timezone
import threading
import time
from typing import Any, Dict, List, Optional
import pyperclip
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.Clipboard")


class ClipboardManager:
    """Manages reading, writing, and history auditing for the Windows clipboard."""

    def __init__(self, max_history: int = 50) -> None:
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []
        self._last_text = ""
        self._lock = threading.Lock()

    def get_text(self) -> str:
        """Read current text from clipboard with fallback to internal buffer."""
        try:
            val = pyperclip.paste()
            if val:
                return val
        except Exception as exc:
            logger.debug(f"OS clipboard paste failed: {exc}. Using memory buffer.")
        return self._last_text

    def set_text(self, text: str) -> bool:
        """Write text to clipboard and record history."""
        try:
            try:
                pyperclip.copy(text)
            except Exception as copy_err:
                logger.debug(f"OS clipboard copy failed (headless/sandbox): {copy_err}. Storing in memory.")

            self._record_entry(text)
            event_bus.publish_sync(
                Event(
                    event_type=EventType.CLIPBOARD_CHANGED,
                    payload={"text": text[:100]},
                )
            )
            return True
        except Exception as exc:
            logger.error(f"Error setting clipboard: {exc}")
            return False

    def _record_entry(self, text: str) -> None:
        """Record a new clipboard entry to history if unique."""
        if not text or text == self._last_text:
            return

        with self._lock:
            self._last_text = text
            entry = {
                "text": text,
                "length": len(text),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._history.insert(0, entry)
            if len(self._history) > self.max_history:
                self._history.pop()

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent clipboard entries."""
        with self._lock:
            return list(self._history[:limit])

    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """Search clipboard history by substring."""
        q = query.lower()
        with self._lock:
            return [item for item in self._history if q in item["text"].lower()]


# Singleton clipboard manager instance
clipboard_manager = ClipboardManager()
