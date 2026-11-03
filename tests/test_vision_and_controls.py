"""Unit tests for Vision, Screen capture, OCR, Clipboard, and Browser tools."""

import tempfile
import unittest
from PIL import Image

from jarvis.vision.screen_capture import screen_capture
from jarvis.vision.ocr_engine import ocr_engine
from jarvis.tools.clipboard.clipboard_manager import ClipboardManager
from jarvis.tools.browser.browser_controller import BrowserController


class TestVisionAndControls(unittest.TestCase):
    """Test suite for screen capture, OCR, clipboard management, and browser control."""

    def test_screen_capture_and_encoding(self):
        """Verify desktop screenshot capture and base64 serialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = f"{tmp_dir}/test_screenshot.png"
            res = screen_capture.capture_full_screen(save_path=out_file)

            self.assertTrue(res["success"])
            self.assertGreater(res["width"], 0)
            self.assertGreater(res["height"], 0)

            # Test region capture
            reg_res = screen_capture.capture_region(0, 0, 80, 60, save_path=f"{tmp_dir}/reg.png")
            self.assertTrue(reg_res["success"])
            self.assertEqual(reg_res["width"], 80)
            self.assertEqual(reg_res["height"], 60)

            # Test base64 encoding
            b64_str = screen_capture.to_base64(reg_res["image"])
            self.assertIsInstance(b64_str, str)
            self.assertGreater(len(b64_str), 0)

    def test_ocr_engine_processing(self):
        """Verify image text extraction interface."""
        dummy_img = Image.new("RGB", (200, 60), color=(255, 255, 255))
        res = ocr_engine.extract_text_from_image(dummy_img)
        self.assertTrue(res["success"])
        self.assertIn("engine", res)

    def test_clipboard_manager_history(self):
        """Verify clipboard set, get, history tracking, and search."""
        cm = ClipboardManager()
        test_val = "JARVIS_AUTOMATION_CLIPBOARD_KEY_9988"

        # Set & Get
        success = cm.set_text(test_val)
        self.assertTrue(success)
        retrieved = cm.get_text()
        self.assertEqual(retrieved, test_val)

        # History
        history = cm.get_history()
        self.assertTrue(any(item["text"] == test_val for item in history))

        # Search
        search_res = cm.search_history("CLIPBOARD_KEY_9988")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["text"], test_val)


if __name__ == "__main__":
    unittest.main()
