"""Screen capture engine for full desktop, active window, and regions."""

from __future__ import annotations
import base64
import ctypes
from datetime import datetime
import io
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageGrab
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.ScreenCapture")


def _win32_gdi_screenshot() -> Optional[Image.Image]:
    """Capture desktop display directly via Win32 GDI BitBlt API."""
    if not hasattr(ctypes, "windll"):
        return None
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)

        hdesktop = user32.GetDesktopWindow()
        desktop_dc = user32.GetWindowDC(hdesktop)
        img_dc = gdi32.CreateCompatibleDC(desktop_dc)

        mem_bitmap = gdi32.CreateCompatibleBitmap(desktop_dc, w, h)
        gdi32.SelectObject(img_dc, mem_bitmap)

        # SRCCOPY = 0x00CC0020
        res = gdi32.BitBlt(img_dc, 0, 0, w, h, desktop_dc, 0, 0, 0x00CC0020)
        if not res:
            gdi32.DeleteObject(mem_bitmap)
            gdi32.DeleteDC(img_dc)
            user32.ReleaseDC(hdesktop, desktop_dc)
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf_size = w * h * 4
        buf = (ctypes.c_char * buf_size)()

        lines = gdi32.GetDIBits(img_dc, mem_bitmap, 0, h, buf, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(mem_bitmap)
        gdi32.DeleteDC(img_dc)
        user32.ReleaseDC(hdesktop, desktop_dc)

        if lines == h:
            img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
            return img.convert("RGB")
    except Exception as exc:
        logger.debug(f"Win32 GDI screenshot failed: {exc}")
    return None


class ScreenCaptureEngine:
    """Captures and encodes desktop screenshots."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def capture_full_screen(
        self,
        save_path: Optional[str] = None,
        open_after: bool = False,
    ) -> Dict[str, Any]:
        """Capture the primary or entire virtual desktop screen using pyautogui, ImageGrab, or Win32 GDI."""
        try:
            img = None

            # 1. Try pyautogui
            try:
                import pyautogui
                img = pyautogui.screenshot()
            except Exception as e_pyauto:
                logger.debug(f"pyautogui.screenshot failed ({e_pyauto}); trying ImageGrab...")

            # 2. Try ImageGrab
            if img is None:
                try:
                    img = ImageGrab.grab(all_screens=True)
                except Exception:
                    try:
                        img = ImageGrab.grab()
                    except Exception as e_grab:
                        logger.debug(f"ImageGrab failed ({e_grab}); trying Win32 GDI...")

            # 3. Try Win32 GDI BitBlt
            if img is None:
                img = _win32_gdi_screenshot()

            if img is None:
                raise RuntimeError("Failed to capture screen image through all display drivers.")

            saved_file = self._persist_image(img, save_path)

            # Publish event for UI toast confirmation
            event_bus.publish_sync(
                Event(
                    event_type=EventType.SCREENSHOT_TAKEN,
                    payload={
                        "path": saved_file,
                        "size": img.size,
                        "message": "Screenshot saved successfully, Sir.",
                    },
                )
            )

            # Speak confirmation aloud
            try:
                from jarvis.voice.tts import tts_engine
                tts_engine.speak("Screenshot saved successfully, Sir.", wait=False)
            except Exception:
                pass

            if open_after:
                try:
                    os.startfile(saved_file)
                except Exception as open_err:
                    logger.debug(f"Could not open screenshot viewer: {open_err}")

            return {
                "status": "success",
                "success": True,
                "path": saved_file,
                "width": img.width,
                "height": img.height,
                "image": img,
                "message": "Screenshot saved successfully, Sir.",
                "feedback": "Screenshot saved successfully, Sir.",
            }
        except Exception as exc:
            logger.error(f"Failed to capture full screen: {exc}")
            return {
                "status": "error",
                "success": False,
                "error": str(exc),
                "feedback": f"Screenshot failed: {exc}",
            }

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture a specified bounding box region."""
        try:
            bbox = (x, y, x + width, y + height)
            img = None
            try:
                import pyautogui
                img = pyautogui.screenshot(region=(x, y, width, height))
            except Exception:
                try:
                    img = ImageGrab.grab(bbox=bbox)
                except Exception:
                    full = _win32_gdi_screenshot()
                    if full:
                        img = full.crop(bbox)

            if img is None:
                raise RuntimeError("Failed to capture region.")

            saved_file = self._persist_image(img, save_path)
            return {
                "status": "success",
                "success": True,
                "path": saved_file,
                "bbox": bbox,
                "width": img.width,
                "height": img.height,
                "image": img,
            }
        except Exception as exc:
            logger.error(f"Failed to capture region: {exc}")
            return {"status": "error", "success": False, "error": str(exc)}

    def to_base64(self, img: Image.Image, format: str = "PNG") -> str:
        """Convert a PIL Image to base64 string for multimodal LLM vision input."""
        buffered = io.BytesIO()
        img.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _persist_image(self, img: Image.Image, save_path: Optional[str] = None) -> str:
        """Save captured image to a dedicated screenshots/ directory."""
        if save_path:
            p = Path(save_path).expanduser().resolve()
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = self.settings.BASE_DIR / "screenshots"
            p = screenshots_dir / f"screenshot_{ts}.png"

        p.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(p), "PNG")
        logger.info(f"Saved screenshot to: {p}")
        return str(p)


# Singleton screen capture instance
screen_capture = ScreenCaptureEngine()
