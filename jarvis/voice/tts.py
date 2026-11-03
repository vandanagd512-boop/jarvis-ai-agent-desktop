"""Windows native Text-to-Speech engine using SAPI5."""

from __future__ import annotations
import queue
import threading
import time
from typing import Optional
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.exceptions import VoiceError
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.TTS")


class TextToSpeechEngine:
    """Thread-safe Text-to-Speech engine utilizing Windows SAPI5 via pyttsx3."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._speech_queue: queue.Queue[str] = queue.Queue()
        self._is_running = True
        self._worker_thread: Optional[threading.Thread] = None
        self._engine = None
        self._lock = threading.Lock()

        self._start_worker()

    def _init_engine(self):
        """Initialize or re-initialize the pyttsx3 engine in the worker thread."""
        try:
            import pyttsx3
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.settings.VOICE_RATE)
            engine.setProperty("volume", self.settings.VOICE_VOLUME)

            voices = engine.getProperty("voices")
            if voices:
                # Select male (David) or female (Zira) based on configuration
                target_gender = self.settings.VOICE_GENDER.lower()
                chosen_voice = voices[0]
                for v in voices:
                    if target_gender in v.name.lower() or (target_gender == "female" and "zira" in v.name.lower()):
                        chosen_voice = v
                        break
                engine.setProperty("voice", chosen_voice.id)
                logger.debug(f"Selected TTS voice: {chosen_voice.name}")

            return engine
        except Exception as exc:
            logger.warning(f"Failed to initialize pyttsx3 SAPI5: {exc}. Falling back to console output.")
            return None

    def _worker_loop(self) -> None:
        """Background worker consuming and speaking queued utterances."""
        # Initialize COM on the worker thread for Windows SAPI5
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        self._engine = self._init_engine()

        while self._is_running:
            try:
                text = self._speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not text or not text.strip():
                self._speech_queue.task_done()
                continue

            logger.info(f"Speaking: '{text}'")
            event_bus.publish_sync(Event(event_type=EventType.TTS_STARTED, payload={"text": text}))

            try:
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
                else:
                    # Fallback text display if audio driver is missing
                    print(f"\n[JARVIS]: {text}\n")
            except Exception as exc:
                logger.error(f"Error during TTS playback: {exc}")
            finally:
                event_bus.publish_sync(Event(event_type=EventType.TTS_FINISHED, payload={"text": text}))
                self._speech_queue.task_done()

        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def _start_worker(self) -> None:
        """Start the background speech worker thread."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="JARVIS-TTS-Worker",
        )
        self._worker_thread.start()

    def speak(self, text: str, wait: bool = False) -> None:
        """Enqueue speech utterance.

        If wait=True, blocks until the utterance has finished playing.
        """
        if not text:
            return
        self._speech_queue.put(text)
        if wait:
            self._speech_queue.join()

    def set_rate(self, rate: int) -> None:
        """Adjust speech rate (words per minute)."""
        self.settings.VOICE_RATE = max(100, min(300, rate))
        if self._engine:
            self._engine.setProperty("rate", self.settings.VOICE_RATE)

    def set_volume(self, volume: float) -> None:
        """Adjust speech volume (0.0 to 1.0)."""
        self.settings.VOICE_VOLUME = max(0.0, min(1.0, volume))
        if self._engine:
            self._engine.setProperty("volume", self.settings.VOICE_VOLUME)

    def stop(self) -> None:
        """Shut down speech worker gracefully."""
        self._is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)


# Singleton TTS instance
tts_engine = TextToSpeechEngine()
