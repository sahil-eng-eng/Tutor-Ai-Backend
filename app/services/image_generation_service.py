"""
Image Generation Service — integrates with the nano-banana API to produce
educational diagrams from visual_hint text.

Uses nano-banana's *callback* pattern:
  1.  POST  →  nano-banana   (returns a taskId immediately)
  2.  nano-banana later POSTs to our callback endpoint with the resultImageUrl
  3.  An asyncio.Future bridges the two — _generate_single_image awaits the
      Future while the callback endpoint resolves it.

Sequential per-block: hints are processed in block order (b1-vh1, b1-vh2, b2-vh1 …).
Each one waits for the callback before moving on so image URLs are written into
the content_script in the correct order and persisted to the DB.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.session import SessionSegment

logger = logging.getLogger("ai_tutor")

# ── Pending callback registry ─────────────────────────────────────────
# Maps  taskId → asyncio.Future[str]   (str = resultImageUrl)
_pending_tasks: dict[str, asyncio.Future[str]] = {}


def resolve_callback(task_id: str, image_url: str) -> bool:
    """Called by the callback API endpoint when nano-banana POSTs back.

    Resolves the pending Future so _generate_single_image can continue.
    Returns True if the taskId was found and resolved.
    """
    future = _pending_tasks.pop(task_id, None)
    if future is not None and not future.done():
        future.set_result(image_url)
        logger.info("Resolved callback for taskId=%s → %s", task_id, image_url[:80])
        return True
    logger.warning("resolve_callback: unknown or already-resolved taskId=%s", task_id)
    return False


# ── Data structures ────────────────────────────────────────────────────

@dataclass
class VisualHintLocation:
    """Identifies a single visual_hint inside a content_script."""
    block_id: str
    block_title: str
    section_index: int
    element_index: int
    raw_text: str


# ── Public helpers ─────────────────────────────────────────────────────

def collect_visual_hints(
    content_script: dict, *, only_missing: bool = False
) -> list[VisualHintLocation]:
    """Walk blocks → sections → elements in order; return all visual_hint locations.

    If *only_missing* is True, skip hints that already have an ``image_url``.
    """
    hints: list[VisualHintLocation] = []
    for block in content_script.get("blocks", []):
        block_id = block.get("id", "")
        block_title = block.get("title", "")
        for si, section in enumerate(block.get("sections", [])):
            for ei, element in enumerate(section.get("elements", [])):
                if element.get("type") == "visual_hint":
                    if only_missing and element.get("image_url"):
                        continue
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


# ── Internal helpers ───────────────────────────────────────────────────

async def _generate_single_image(prompt: str) -> Optional[str]:
    """Fire a generation request to nano-banana and wait for the callback.

    1. POST to nano-banana with callBackUrl  →  get taskId
    2. Create asyncio.Future keyed by taskId
    3. Await the Future (callback endpoint will resolve it)
    4. Return the image URL or None on timeout / error
    """
    if not settings.NANOBANANA_ENABLED:
        print('Nano-banana disabled; skipping image gen')
        logger.debug("Nano-banana disabled; skipping image gen")
        return None
    if not settings.NANOBANANA_API_URL or not settings.NANOBANANA_API_KEY:
        print('Nano-banana URL or API key not configured; skipping image gen')
        logger.debug("Nano-banana URL or API key not configured; skipping image gen")
        return None
    if not settings.NANOBANANA_CALLBACK_BASE_URL:
        print('Nano-banana callback URL not configured; skipping image gen')
        logger.warning("NANOBANANA_CALLBACK_BASE_URL not set; cannot receive callbacks. Skipping image gen.")
        return None

    callback_url = f"{settings.NANOBANANA_CALLBACK_BASE_URL.rstrip('/')}/api/v1/images/callback"
    print('Sending image generation request to nano-banana with prompt:', callback_url)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                settings.NANOBANANA_API_URL,
                json={
                    "prompt": prompt,
                    "type": "TEXTTOIAMGE",       # note: nano-banana uses this spelling
                    "numImages": 1,
                    "image_size": "16:9",
                    "callBackUrl": callback_url,
                },
                headers={
                    "Authorization": f"Bearer {settings.NANOBANANA_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            print('Nano-banana response:', data)

        # Extract taskId from immediate response: {code: 200, data: {taskId: "..."}}
        task_id = (data.get("data") or {}).get("taskId")
        if not task_id:
            logger.error("Nano-banana did not return a taskId. Response: %s", data)
            return None

        logger.info("Nano-banana accepted request — taskId=%s, waiting for callback…", task_id)
        print('Nano-banana accepted request — taskId=', task_id, ', waiting for callback…')
        # Create a Future and register it for the callback to resolve
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        _pending_tasks[task_id] = future

        try:
            image_url: str = await asyncio.wait_for(
                future, timeout=settings.NANOBANANA_TIMEOUT_SECONDS,
            )
            print('------------------------------------')
            print(image_url)
            return image_url
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for callback (taskId=%s)", task_id)
            _pending_tasks.pop(task_id, None)
            return None

    except Exception:
        print('--------------------------------------------------------------------')
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


# ── Main entry point (background task) ─────────────────────────────────

async def fire_image_generation(
    session_id: UUID,
    segment_order: int,
    content_script: dict,
    image_ready_queue: Optional[asyncio.Queue] = None,
) -> None:
    """Background task: sequentially process image requests for all visual_hints.

    Each hint is sent to nano-banana, then we *await* the callback before
    moving to the next hint.  As each image resolves, the URL is written into
    the in-memory content_script and persisted to the DB.

    Hints that already have an ``image_url`` are skipped (idempotent re-runs
    are safe and avoid duplicate nano-banana API calls).

    If *image_ready_queue* is provided, ``(block_id, image_url)`` tuples are
    pushed onto it so the SSE streaming generator can emit ``image_ready``
    events to the frontend in real-time.
    """
    hints = collect_visual_hints(content_script, only_missing=True)
    if not hints:
        return

    logger.info(
        "Starting image generation for %d visual hints (session=%s, segment=%d)",
        len(hints), session_id, segment_order,
    )

    for i, hint in enumerate(hints):
        prompt = enrich_prompt(hint, content_script)
        logger.info(
            "Generating image %d/%d — block=%s prompt=%.80s",
            i + 1, len(hints), hint.block_id, prompt,
        )
        image_url = await _generate_single_image(prompt)
        if image_url:
            _apply_image_url(content_script, hint, image_url)
            await _persist_content_script(session_id, segment_order, content_script)
            if image_ready_queue is not None:
                await image_ready_queue.put((hint.block_id, image_url))
            logger.info(
                "Image ready: block=%s, sec=%d, el=%d, url=%s",
                hint.block_id, hint.section_index, hint.element_index, image_url[:80],
            )
        else:
            logger.warning(
                "Image generation returned no URL: block=%s, sec=%d, el=%d",
                hint.block_id, hint.section_index, hint.element_index,
            )

    # Signal completion so the SSE generator stops waiting
    if image_ready_queue is not None:
        await image_ready_queue.put(None)
