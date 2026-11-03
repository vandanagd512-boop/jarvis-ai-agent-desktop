"""Continuous voice interaction state machine and background listener."""

from __future__ import annotations
from enum import Enum
import threading
import time
from typing import Optional
from jarvis.brain.router import action_router
from jarvis.core.config import get_settings
from jarvis.core.context import runtime_context
from jarvis.core.logger import get_logger
from jarvis.voice.stt import stt_engine
from jarvis.voice.tts import tts_engine
from jarvis.voice.wake_word import wake_word_detector

logger = get_logger("JARVIS.VoiceListener")


class VoiceState(str, Enum):
    """States of the continuous voice interaction engine."""
    SLEEPING = "SLEEPING"      # Waiting for wake-word
    LISTENING = "LISTENING"    # Actively recording user query
    THINKING = "THINKING"      # Brain reasoning & tool execution
    SPEAKING = "SPEAKING"      # Synthesizing and delivering response


class VoiceListener:
    """Manages continuous background microphone monitoring and conversational turns."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.state = VoiceState.SLEEPING
        self._is_active = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def set_state(self, new_state: VoiceState) -> None:
        """Update current voice state and runtime context."""
        with self._lock:
            self.state = new_state
            runtime_context.is_listening = new_state in (VoiceState.SLEEPING, VoiceState.LISTENING)
            runtime_context.is_thinking = new_state == VoiceState.THINKING
            runtime_context.is_speaking = new_state == VoiceState.SPEAKING
            logger.debug(f"Voice state transitioned to: {new_state.value}")

    def _loop(self) -> None:
        """Main listening cycle."""
        logger.info("Continuous voice listening thread started.")

        while self._is_active:
            try:
                if self.state == VoiceState.SLEEPING:
                    # Listen for brief wake-word utterance
                    text = stt_engine.listen_from_microphone(timeout=3.0, phrase_time_limit=4.0)
                    if not text:
                        continue

                    is_wake, command = wake_word_detector.check(text)
                    if is_wake:
                        if command:
                            # User said "Jarvis, what's the weather" in a single breath
                            self._handle_command(command)
                        else:
                            # User only said "Jarvis", acknowledge and enter active listening
                            self.set_state(VoiceState.SPEAKING)
                            tts_engine.speak("At your service, Sir.", wait=True)
                            self.set_state(VoiceState.LISTENING)

                elif self.state == VoiceState.LISTENING:
                    # User woke JARVIS up, record the actual command
                    command = stt_engine.listen_from_microphone(timeout=6.0, phrase_time_limit=12.0)
                    if command:
                        self._handle_command(command)
                    else:
                        # Timeout or silence, return to sleeping
                        self.set_state(VoiceState.SLEEPING)

                elif self.state in (VoiceState.THINKING, VoiceState.SPEAKING):
                    # Busy; wait briefly
                    time.sleep(0.1)

            except Exception as exc:
                logger.error(f"Error in voice listener loop: {exc}")
                time.sleep(0.5)

    def _handle_command(self, command: str) -> None:
        """Route transcribed command to brain reasoning and speak the response."""
        self.set_state(VoiceState.THINKING)
        logger.info(f"Executing voice command: '{command}'")

        result = action_router.process_query(command, conversation_id="voice_session")
        response_text = result.get("response", "Command executed, Sir.")

        self.set_state(VoiceState.SPEAKING)
        # Speak concise summary without blocking listener thread
        import re
        clean = re.sub(r"[\*#_`]", "", response_text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        spoken_text = " ".join(sentences[:2]).strip() if len(sentences) > 2 else clean
        if len(spoken_text) > 250:
            spoken_text = spoken_text[:240] + "."

        tts_engine.speak(spoken_text, wait=False)

        # Return to sleeping state immediately so listener is ready for next command
        self.set_state(VoiceState.SLEEPING)

    def start(self) -> None:
        """Start background continuous listening."""
        if self._is_active:
            return
        self._is_active = True
        self.set_state(VoiceState.SLEEPING)
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="JARVIS-VoiceListener",
        )
        self._thread.start()
        logger.info("VoiceListener service running.")

    def stop(self) -> None:
        """Stop listening thread gracefully."""
        self._is_active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.set_state(VoiceState.SLEEPING)
        logger.info("VoiceListener service stopped.")


# Singleton voice listener instance
voice_listener = VoiceListener()
