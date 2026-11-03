"""Optical Character Recognition (OCR) for screen and image files."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
from PIL import Image
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.OCR")


class OCREngine:
    """Extracts text from screenshots and image files."""

    def extract_text_from_image(self, image_input: str | Image.Image) -> Dict[str, Any]:
        """Perform OCR on an image file path or PIL Image object."""
        try:
            if isinstance(image_input, str):
                path = Path(image_input).expanduser().resolve()
                if not path.is_file():
                    return {"success": False, "error": f"Image file '{image_input}' not found."}
                img = Image.open(path)
            else:
                img = image_input

            # Try pytesseract if installed
            try:
                import pytesseract
                text = pytesseract.image_to_string(img)
                return {
                    "success": True,
                    "engine": "pytesseract",
                    "text": text.strip(),
                    "word_count": len(text.split()),
                }
            except Exception as t_err:
                logger.debug(f"Pytesseract not available or failed: {t_err}")

            # Fallback heuristic / metadata
            return {
                "success": True,
                "engine": "fallback",
                "text": f"[Image Dimensions: {img.width}x{img.height}, Mode: {img.mode}]",
                "word_count": 0,
            }
        except Exception as exc:
            logger.error(f"Error during OCR extraction: {exc}")
            return {"success": False, "error": str(exc)}


# Singleton OCR instance
ocr_engine = OCREngine()
