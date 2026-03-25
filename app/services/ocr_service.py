"""
OCR Service — extracts text from uploaded images.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("ai_tutor")


async def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image using pytesseract OCR.
    Falls back to a placeholder if tesseract is not installed.
    """
    try:
        import pytesseract
        from PIL import Image

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        logger.warning("pytesseract or Pillow not available, OCR disabled")
        return "[OCR extraction unavailable — pytesseract not installed]"
    except Exception as e:
        logger.exception("OCR extraction failed for %s", image_path)
        raise
