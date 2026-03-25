"""
File handling utilities — upload, validation, storage.
"""

from __future__ import annotations

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

import aiofiles

from app.config import settings

logger = logging.getLogger("ai_tutor")

ALLOWED_EXTENSIONS = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
    "document": {".pdf", ".doc", ".docx", ".txt", ".rtf"},
    "all": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf", ".doc", ".docx", ".txt", ".rtf"},
}


def validate_file_extension(filename: str, allowed_type: str = "all") -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS.get(allowed_type, ALLOWED_EXTENSIONS["all"])


def validate_file_size(size_bytes: int) -> bool:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes


async def save_upload(
    file_content: bytes,
    original_filename: str,
    subfolder: str = "general",
) -> str:
    """Save uploaded file to disk and return the relative path."""
    ext = Path(original_filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    folder = Path(settings.UPLOAD_DIR) / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / safe_name

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)

    return str(file_path)


async def delete_file(file_path: str) -> bool:
    """Delete a file from disk."""
    try:
        path = Path(file_path)
        if path.exists():
            os.remove(path)
            return True
    except Exception:
        logger.exception("Failed to delete file: %s", file_path)
    return False
