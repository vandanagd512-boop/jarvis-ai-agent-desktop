"""Media controls and volume adjustment using Windows Virtual Keys."""

import ctypes
import time
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.MediaControls")

user32 = getattr(ctypes, "windll", None).user32 if hasattr(ctypes, "windll") else None

# Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_F5 = 0x74

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _press_key(vk_code: int) -> None:
    """Simulate key press and release."""
    if not user32:
        return
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


class MediaControls:
    """Controls playback and volume on Windows."""

    @staticmethod
    def play_pause() -> bool:
        """Toggle media play / pause on Windows and YouTube."""
        logger.info("Triggered Media: Play/Pause")
        _press_key(VK_MEDIA_PLAY_PAUSE)
        try:
            import pyautogui
            pyautogui.press("k")
        except Exception:
            pass
        return True

    @staticmethod
    def next_track() -> bool:
        """Skip to next track or YouTube video."""
        logger.info("Triggered Media: Next Track")
        _press_key(VK_MEDIA_NEXT_TRACK)
        try:
            import pyautogui
            pyautogui.hotkey("shift", "n")
        except Exception:
            pass
        return True

    @staticmethod
    def prev_track() -> bool:
        """Skip to previous track."""
        logger.info("Triggered Media: Previous Track")
        _press_key(VK_MEDIA_PREV_TRACK)
        return True

    @staticmethod
    def refresh_page() -> bool:
        """Reload the currently active browser or window (F5)."""
        logger.info("Triggered: Page Refresh (F5)")
        _press_key(VK_F5)
        return True

    @staticmethod
    def stop() -> bool:
        """Stop media playback."""
        logger.info("Triggered Media: Stop")
        _press_key(VK_MEDIA_STOP)
        return True

    @staticmethod
    def volume_up(steps: int = 2) -> bool:
        """Increase volume by given number of increments (each step is 2%)."""
        logger.info(f"Triggered Volume Up: {steps} steps")
        for _ in range(max(1, steps)):
            _press_key(VK_VOLUME_UP)
            time.sleep(0.02)
        return True

    @staticmethod
    def volume_down(steps: int = 2) -> bool:
        """Decrease volume by given number of increments (each step is 2%)."""
        logger.info(f"Triggered Volume Down: {steps} steps")
        for _ in range(max(1, steps)):
            _press_key(VK_VOLUME_DOWN)
            time.sleep(0.02)
        return True

    @staticmethod
    def toggle_mute() -> bool:
        """Toggle master volume mute."""
        logger.info("Triggered Volume: Toggle Mute")
        _press_key(VK_VOLUME_MUTE)
        return True


# Singleton instance
media_controls = MediaControls()
