"""
Image Generation Service — integrates with the nano-banana utility to produce
educational diagrams from visual_hint text.

Sequential fire-and-forget: requests are dispatched in block-order (b1-vh1,
b1-vh2, b2-vh1 …) but each request is non-blocking.  As soon as any image
resolves, the result is written back to the in-memory content_script dict and
persisted to the DB so the SSE parser can pick it up.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.session import SessionSegment

logger = logging.getLogger("ai_tutor")

# ── Data structures ────────────────────────────────────────────────────

@dataclass
class VisualHintLocation:
    """Identifies a single visual_hint inside a content_script."""
    block_id: str
    block_title: str
    section_index: int
    element_index: int
    raw_text: str


# ── Public API ─────────────────────────────────────────────────────────

def collect_visual_hints(content_script: dict) -> list[VisualHintLocation]:
    """Walk blocks → sections → elements in order; return all visual_hint locations."""
    hints: list[VisualHintLocation] = []
    for block in content_script.get("blocks", []):
        block_id = block.get("id", "")
        block_title = block.get("title", "")
        for si, section in enumerate(block.get("sections", [])):
            for ei, element in enumerate(section.get("elements", [])):
                if element.get("type") == "visual_hint":
                    hints.append(VisualHintLocation(
                        block_id=block_id,
                        block_title=block_title,
                        section_index=si,
                        element_index=ei,
                        raw_text=element.get("text", ""),
                    ))
    return hints


def enrich_prompt(hint: VisualHintLocation, content_script: dict) -> str:
    """Build an enriched image-generation prompt from hint + context."""
    topic = content_script.get("topic", "")
    difficulty = content_script.get("difficulty", "intermediate")
    parts = [hint.raw_text.strip()]
    if hint.block_title:
        parts.append(f"Block: {hint.block_title}.")
    if topic:
        parts.append(f"Topic: {topic}.")
    style_map = {
        "beginner": "simple educational diagram, colorful, large labels, minimal detail, suitable for beginners",
        "basic": "clear educational diagram, labeled arrows, bright colors, suitable for learning",
        "intermediate": "educational diagram, clean background, labeled arrows, bright colors, suitable for learning",
        "advanced": "detailed educational diagram, precise labels, professional layout, suitable for advanced learners",
        "expert": "technical diagram, detailed annotations, precise layout, professional scientific style",
    }
    style = style_map.get(difficulty, style_map["intermediate"])
    parts.append(f"Style: {style}.")
    return " ".join(parts)


def _apply_image_url(content_script: dict, hint: VisualHintLocation, image_url: str) -> None:
    """Write image_url into the correct element of the in-memory content_script."""
    for block in content_script.get("blocks", []):
        if block.get("id") == hint.block_id:
            try:
                element = block["sections"][hint.section_index]["elements"][hint.element_index]
                element["image_url"] = image_url
            except (IndexError, KeyError):
                logger.warning(
                    "Could not write image_url for hint block=%s sec=%d el=%d",
                    hint.block_id, hint.section_index, hint.element_index,
                )
            return


async def _generate_single_image(prompt: str) -> Optional[str]:
    """Call nano-banana for a single prompt.  Returns the image URL or None."""
    if not settings.NANOBANANA_API_URL or not settings.NANOBANANA_ENABLED:
        logger.debug("Nano-banana disabled or URL not configured; skipping image gen")
        return None
    try:
        async with httpx.AsyncClient(timeout=settings.NANOBANANA_TIMEOUT_SECONDS) as client:
            headers = {}
            if settings.NANOBANANA_API_KEY:
                headers["Authorization"] = f"Bearer {settings.NANOBANANA_API_KEY}"
            resp = await client.post(
                settings.NANOBANANA_API_URL,
                json={"prompt": prompt},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            # Accept either {url: "..."} or {image_url: "..."} or {data: {url: "..."}}
            url = (
                data.get("url")
                or data.get("image_url")
                or (data.get("data", {}) or {}).get("url")
            )
            return url or None
    except Exception:
        logger.exception("Nano-banana image generation failed for prompt (first 80 chars): %s", prompt[:80])
        return None


async def _persist_content_script(session_id: UUID, segment_order: int, content_script: dict) -> None:
    """Write the updated content_script back to the DB."""
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SessionSegment).where(
                    SessionSegment.session_id == session_id,
                    SessionSegment.segment_order == segment_order,
                )
            )
            seg = result.scalar_one_or_none()
            if seg:
                seg.content_script = json.dumps(content_script, ensure_ascii=False)
                await db.commit()
    except Exception:
        logger.exception("Failed to persist content_script after image generation")


async def fire_image_generation(
    session_id: UUID,
    segment_order: int,
    content_script: dict,
) -> None:
    """Background task: sequentially fire image requests for all visual_hints.

    Fires each request and moves on immediately (fire-and-forget via tasks).
    As each image resolves, it is written into the in-memory content_script
    and persisted to the DB.
    """
    hints = collect_visual_hints(content_script)
    if not hints:
        return

    logger.info(
        "Starting image generation for %d visual hints (session=%s, segment=%d)",
        len(hints), session_id, segment_order,
    )

    async def _process_hint(hint: VisualHintLocation) -> None:
        prompt = enrich_prompt(hint, content_script)
        image_url = await _generate_single_image(prompt)
        if image_url:
            _apply_image_url(content_script, hint, image_url)
            await _persist_content_script(session_id, segment_order, content_script)
            logger.info(
                "Image ready: block=%s, sec=%d, el=%d, url=%s",
                hint.block_id, hint.section_index, hint.element_index, image_url[:80],
            )

    # Fire sequentially but don't await each one — use tasks
    tasks: list[asyncio.Task] = []
    for hint in hints:
        task = asyncio.create_task(_process_hint(hint))
        tasks.append(task)
        # Small stagger to respect rate limits (sequential firing order)
        await asyncio.sleep(0.15)

    # Wait for all to complete (so the background task itself stays alive)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Image gen task %d failed: %s", i, result)
