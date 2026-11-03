"""Speech-to-Text (STT) input processing using SpeechRecognition."""

from __future__ import annotations
from typing import Optional
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger

import threading

logger = get_logger("JARVIS.STT")

_mic_lock = threading.Lock()


def _amplify_wav(wav_path: str, target_peak_ratio: float = 0.85) -> None:
    """Normalize and amplify audio volume in a WAV file so quiet speech is recognized cleanly."""
    try:
        import struct
        import wave

        with wave.open(wav_path, "rb") as wf:
            params = wf.getparams()
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)

        if not frames or params.sampwidth != 2:
            return

        fmt = f"<{n_frames * params.nchannels}h"
        samples = list(struct.unpack(fmt, frames))
        if not samples:
            return

        max_val = max(abs(s) for s in samples)
        if max_val < 50 or max_val >= 28000:
            return

        gain = min(8.0, (32767 * target_peak_ratio) / max_val)
        amplified = [max(-32768, min(32767, int(s * gain))) for s in samples]

        packed = struct.pack(fmt, *amplified)
        with wave.open(wav_path, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(packed)
    except Exception as exc:
        logger.debug(f"WAV audio amplification note: {exc}")


def _record_audio_native_windows(duration: float = 4.5) -> Optional[str]:
    """Capture audio directly from the Windows microphone using winmm.dll without PyAudio."""
    import ctypes
    import os
    import tempfile
    import time

    with _mic_lock:
        tmp_wav = os.path.join(tempfile.gettempdir(), f"jarvis_mic_{int(time.time() * 1000)}.wav")
        winmm = ctypes.windll.winmm

        try:
            alias = f"rec_{int(time.time() * 1000) % 100000}"
            winmm.mciSendStringW(f"open new type waveaudio alias {alias}", None, 0, None)
            winmm.mciSendStringW(f"record {alias}", None, 0, None)
            time.sleep(duration)
            winmm.mciSendStringW(f'save {alias} "{tmp_wav}"', None, 0, None)
            winmm.mciSendStringW(f"close {alias}", None, 0, None)

            if os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 500:
                _amplify_wav(tmp_wav)
                return tmp_wav
        except Exception as exc:
            logger.debug(f"Native Windows audio capture error: {exc}")
        return None


class SpeechToTextEngine:
    """Captures microphone audio and transcribes spoken utterances into text."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._recognizer = None
        self._has_pyaudio = False
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.settings.STT_ENERGY_THRESHOLD
            self._recognizer.pause_threshold = self.settings.STT_PAUSE_THRESHOLD
            self._recognizer.dynamic_energy_threshold = True
            logger.info("SpeechRecognizer initialized successfully.")

            # Check if PyAudio is available for sr.Microphone()
            try:
                sr.Microphone()
                self._has_pyaudio = True
                logger.info("PyAudio available for microphone input.")
            except Exception:
                self._has_pyaudio = False
                logger.info("PyAudio not present; enabled native Windows multimedia recording backend (winmm.dll).")
        except Exception as exc:
            logger.warning(f"Failed to initialize SpeechRecognition: {exc}")
            self._recognizer = None

    def listen_from_microphone(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> Optional[str]:
        """Record audio from default microphone and transcribe to text."""
        if not self._recognizer:
            logger.warning("Recognizer not available.")
            return None

        # If PyAudio is missing, directly use native Windows multimedia capture
        if not self._has_pyaudio:
            wav_path = _record_audio_native_windows(duration=min(phrase_time_limit, 5.0))
            if wav_path:
                try:
                    text = self.transcribe_audio_file(wav_path)
                    try:
                        import os
                        os.remove(wav_path)
                    except Exception:
                        pass
                    if text and text.strip():
                        cleaned = text.strip()
                        logger.info(f"Transcribed audio (native Windows backend): '{cleaned}'")
                        event_bus.publish_sync(
                            Event(
                                event_type=EventType.SPEECH_TRANSCRIBED,
                                payload={"transcription": cleaned},
                            )
                        )
                        return cleaned
                except Exception as t_err:
                    logger.debug(f"Native audio transcribe failed: {t_err}")
            return None

        import speech_recognition as sr

        try:
            with sr.Microphone() as source:
                logger.debug("Listening for audio input...")
                event_bus.publish_sync(Event(event_type=EventType.SPEECH_RECORDING_STARTED))

                # Adjust for ambient noise briefly
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

                event_bus.publish_sync(Event(event_type=EventType.SPEECH_RECORDING_ENDED))
                logger.debug("Captured audio, transcribing...")

                # Transcribe using Google Speech Recognition
                text = self._recognizer.recognize_google(audio)
                if text and text.strip():
                    cleaned_text = text.strip()
                    logger.info(f"Transcribed audio: '{cleaned_text}'")
                    event_bus.publish_sync(
                        Event(
                            event_type=EventType.SPEECH_TRANSCRIBED,
                            payload={"transcription": cleaned_text},
                        )
                    )
                    return cleaned_text
                return None

        except sr.WaitTimeoutError:
            logger.debug("Microphone listen timed out (silence).")
            return None
        except sr.UnknownValueError:
            logger.debug("Could not understand audio input.")
            return None
        except sr.RequestError as exc:
            logger.warning(f"STT recognition service error: {exc}")
            return None
        except (AttributeError, OSError, Exception) as exc:
            err_msg = str(exc)
            if "PyAudio" in err_msg or "pyaudio" in err_msg:
                # Automatic native Windows recording fallback without PyAudio
                wav_path = _record_audio_native_windows(duration=min(phrase_time_limit, 3.5))
                if wav_path:
                    try:
                        text = self.transcribe_audio_file(wav_path)
                        try:
                            import os
                            os.remove(wav_path)
                        except Exception:
                            pass
                        if text and text.strip():
                            cleaned = text.strip()
                            logger.info(f"Transcribed audio (native Windows backend): '{cleaned}'")
                            event_bus.publish_sync(
                                Event(
                                    event_type=EventType.SPEECH_TRANSCRIBED,
                                    payload={"transcription": cleaned},
                                )
                            )
                            return cleaned
                    except Exception as t_err:
                        logger.debug(f"Native audio transcribe failed: {t_err}")
                return None

            logger.error(f"Unexpected error capturing microphone audio: {exc}")
            return None

    def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        """Transcribe a recorded WAV/AIFF audio file."""
        if not self._recognizer:
            return None

        # Optimize audio loudness before feeding to STT recognizer
        _amplify_wav(audio_path)

        import speech_recognition as sr
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self._recognizer.record(source)
                return self._recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            # Silence or non-speech ambient sound
            return None
        except sr.RequestError as exc:
            logger.warning(f"Google STT service network note: {exc}")
            return None
        except Exception as exc:
            logger.debug(f"Audio transcription note: {exc}")
            return None


# Singleton STT instance
stt_engine = SpeechToTextEngine()
