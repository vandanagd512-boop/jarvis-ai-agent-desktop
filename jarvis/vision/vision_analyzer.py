"""Multimodal screen understanding and vision analysis."""

from __future__ import annotations
from typing import Any, Dict, Optional
from jarvis.automations.windows.window_manager import window_manager
from jarvis.brain.gemini_provider import GeminiProvider
from jarvis.core.logger import get_logger
from jarvis.vision.ocr_engine import ocr_engine
from jarvis.vision.screen_capture import screen_capture

logger = get_logger("JARVIS.VisionAnalyzer")


class VisionAnalyzer:
    """Analyzes desktop screen contents using multimodal AI or OCR."""

    def __init__(self) -> None:
        self.gemini = GeminiProvider()

    def analyze_screen(self, query: str = "Describe what is currently visible on the screen.") -> Dict[str, Any]:
        """Capture screenshot and analyze its contents."""
        cap_result = screen_capture.capture_full_screen()
        if not cap_result["success"]:
            return {"success": False, "error": cap_result.get("error")}

        img = cap_result["image"]
        img_path = cap_result["path"]

        # If Gemini is available, run multimodal visual analysis
        if self.gemini.is_available():
            try:
                from google.genai import types
                b64_data = screen_capture.to_base64(img)
                image_part = types.Part.from_bytes(data=b64_data.encode("utf-8"), mime_type="image/png")

                res = self.gemini._client.models.generate_content(
                    model=self.gemini.model_name,
                    contents=[image_part, query],
                )
                analysis_text = res.text if hasattr(res, "text") else "No visual description generated."
                return {
                    "success": True,
                    "engine": "gemini_multimodal",
                    "analysis": analysis_text,
                    "screenshot_path": img_path,
                }
            except Exception as exc:
                logger.warning(f"Gemini vision analysis failed: {exc}. Falling back to OCR.")

        # Offline Fallback: OCR + Window context
        active_win = window_manager.get_foreground_window()
        ocr_res = ocr_engine.extract_text_from_image(img)

        win_title = active_win.title if active_win else "Desktop"
        summary = (
            f"[Offline Screen Analysis]\n"
            f"- Foreground Application: {win_title}\n"
            f"- Screen Dimensions: {img.width}x{img.height}\n"
            f"- Extracted Text Preview: {ocr_res.get('text', '')[:200]}"
        )

        return {
            "success": True,
            "engine": "offline_ocr",
            "analysis": summary,
            "screenshot_path": img_path,
        }


# Singleton vision analyzer instance
vision_analyzer = VisionAnalyzer()
