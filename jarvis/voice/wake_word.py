"""Wake-word detection and command extraction."""

from __future__ import annotations
import re
from typing import Optional, Tuple
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.WakeWord")


class WakeWordDetector:
    """Detects configured wake words and extracts the trailing command."""

    def __init__(self, wake_word: Optional[str] = None) -> None:
        self.settings = get_settings()
        self.wake_word = (wake_word or self.settings.WAKE_WORD).strip().lower()

        # Build regex patterns for wake word detection
        # Matches: "jarvis", "hey jarvis", "ok jarvis", "hi jarvis"
        self._pattern = re.compile(
            rf"\b(?:hey|hi|ok|hello)?\s*{re.escape(self.wake_word)}\b(?:[,.]|\s+)?(.*)",
            re.IGNORECASE,
        )

    def check(self, utterance: str) -> Tuple[bool, str]:
        """Check if an utterance contains the wake word.

        Returns:
            Tuple[bool, str]: (is_detected, extracted_command)
        """
        if not utterance:
            return False, ""

        cleaned = utterance.strip()
        match = self._pattern.search(cleaned)
        if match:
            extracted_cmd = match.group(1).strip()
            logger.info(f"Wake-word '{self.wake_word}' detected! Command: '{extracted_cmd}'")
            event_bus.publish_sync(
                Event(
                    event_type=EventType.WAKE_WORD_DETECTED,
                    payload={"utterance": utterance, "command": extracted_cmd},
                )
            )
            return True, extracted_cmd

        # Direct exact match check
        if cleaned.lower() == self.wake_word:
            logger.info(f"Exact wake-word '{self.wake_word}' detected.")
            event_bus.publish_sync(
                Event(
                    event_type=EventType.WAKE_WORD_DETECTED,
                    payload={"utterance": utterance, "command": ""},
                )
            )
            return True, ""

        # Direct desktop action recognition (voice commands without explicit wake-word prefix)
        lower_u = cleaned.lower()
        direct_prefixes = (
            "open ", "launch ", "start ", "run ",
            "chat ", "chat with ",
            "text ", "message ", "send message", "send whatsapp",
            "call ", "whatsapp call",
            "play ", "search ", "listen to ", "youtube ",
            "next", "skip", "pause", "resume", "stop music", "previous",
            "refresh", "reload",
            "take screenshot", "take a screenshot", "capture screen", "screenshot",
            "volume ", "mute", "unmute",
            "where am i", "my location", "exact place",
            "lock pc", "lock computer", "lock screen",
            "who is ", "what is ", "how to "
        )
        if any(lower_u.startswith(p) for p in direct_prefixes):
            logger.info(f"Direct voice command recognized: '{cleaned}'")
            return True, cleaned

        return False, ""


# Singleton wake word detector
wake_word_detector = WakeWordDetector()
