"""Unit tests for JARVIS Voice and Audio interface subsystem."""

import unittest
from jarvis.voice.wake_word import WakeWordDetector
from jarvis.voice.listener import VoiceListener, VoiceState
from jarvis.voice.tts import TextToSpeechEngine
from jarvis.core.context import runtime_context


class TestVoice(unittest.TestCase):
    """Test suite for wake-word detection, TTS properties, and voice state machine."""

    def setUp(self):
        self.detector = WakeWordDetector(wake_word="jarvis")
        self.listener = VoiceListener()

    def test_wake_word_detection(self):
        """Verify wake-word identification and trailing command extraction."""
        # 1. "Jarvis, open chrome"
        is_wake, cmd = self.detector.check("Jarvis, open chrome")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "open chrome")

        # 2. "Hey Jarvis, what is my battery level"
        is_wake, cmd = self.detector.check("Hey Jarvis, what is my battery level")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "what is my battery level")

        # 3. Exact wake word "Jarvis"
        is_wake, cmd = self.detector.check("Jarvis")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "")

        # 4. Negative test
        is_wake, cmd = self.detector.check("Turn up the sound please")
        self.assertFalse(is_wake)
        self.assertEqual(cmd, "")

        # 5. Direct action test (without wake word)
        is_wake, cmd = self.detector.check("open whatsapp")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "open whatsapp")

    def test_voice_listener_state_transitions(self):
        """Verify state machine and runtime context synchronization."""
        self.listener.set_state(VoiceState.SLEEPING)
        self.assertEqual(self.listener.state, VoiceState.SLEEPING)
        self.assertTrue(runtime_context.is_listening)
        self.assertFalse(runtime_context.is_speaking)

        self.listener.set_state(VoiceState.THINKING)
        self.assertEqual(self.listener.state, VoiceState.THINKING)
        self.assertTrue(runtime_context.is_thinking)
        self.assertFalse(runtime_context.is_listening)

        self.listener.set_state(VoiceState.SPEAKING)
        self.assertEqual(self.listener.state, VoiceState.SPEAKING)
        self.assertTrue(runtime_context.is_speaking)

        # Reset to sleeping
        self.listener.set_state(VoiceState.SLEEPING)

    def test_tts_properties(self):
        """Verify speech rate and volume adjustments."""
        tts = TextToSpeechEngine()
        tts.set_rate(190)
        self.assertEqual(tts.settings.VOICE_RATE, 190)
        tts.set_volume(0.85)
        self.assertEqual(tts.settings.VOICE_VOLUME, 0.85)


if __name__ == "__main__":
    unittest.main()
