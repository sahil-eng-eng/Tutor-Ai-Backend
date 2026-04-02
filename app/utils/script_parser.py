"""
parse_script_to_sse_events — converts a saved content_script into structured SSE data events.

Two formats are supported:

NEW FORMAT (structured JSON blocks):
  content_script is a JSON string with the shape:
    { "topic": "...", "blocks": [ { "id": "b1", "sections": [...] } ] }
  Emits: segment_start, block_start, section_start, text, list_start,
         list_item, list_end, steps_start, step, steps_end, table_start,
         table_row, table_end, tabs_start, tab_start, tab_end, tabs_end,
         accordion, question, summary, visual_hint, section_end, block_end,
         pause, segment_end, [session_end]

LEGACY FORMAT (speech-first text script):
  content_script is a plain text string with inline markup:
    [emotion_tag], <pause:Xms>, [ANIMATION: type=X, description=Y], free text
  Emits: segment_start, emotion, pause, text, whiteboard, segment_end, [session_end]
"""

import asyncio
import json
import re
from typing import AsyncGenerator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _emit(payload: dict) -> str:
    """Serialise a payload dict as an SSE data line."""
    return f"data: {json.dumps(payload)}\n\n"


VALID_EMOTIONS = {"warm", "curious", "calm", "excited", "serious", "friendly", "neutral"}

# ── Legacy text parser tokens ─────────────────────────────────────────────────

_TOKEN_RE = re.compile(
    r"(\[ANIMATION:[^\]]*\])"                   # group 1: animation block
    r"|(<pause:\d+(?:\.\d+)?ms>)"               # group 2: pause marker
    r"|(\[[a-zA-Z_]+\])"                        # group 3: potential emotion tag
    r"|([^<\[\]\s][^<\[\]\n]*?[.!?…])"          # group 4: sentence (lazy, ends at first punct)
    r"|([^<\[\]\s][^<\[\]\n]*)",                # group 5: fallback text run
    re.MULTILINE,
)


# ── Public entry point ─────────────────────────────────────────────────────────

async def parse_script_to_sse_events(
    script: str,
    segment_order: int,
    segment_title: str,
    duration_seconds: int,
    total_segments: int,
    *,
    is_last_segment: bool = False,
    session_id: str = "",
    from_chunk: int = 0,
    emit_terminal_events: bool = True,
    hinglish_map: dict[str, str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Parse a saved content_script and yield fully-formatted SSE ``data: {…}\\n\\n`` strings.

    Detects the script format automatically:
    - If the script is a JSON object with a ``"blocks"`` key  → NEW structured format
    - Otherwise                                                → LEGACY speech-text format

    ``segment_start`` (chunk 0) is ALWAYS emitted first so the frontend can confirm
    a successful reconnect.

    *from_chunk* allows resuming mid-stream: events with ``chunk < from_chunk`` are
    skipped (but ``segment_start`` at chunk 0 is always emitted).

    If *emit_terminal_events* is False, ``segment_end`` and ``session_end`` are
    suppressed — the caller is responsible for emitting them (e.g. after draining
    late-arriving image_ready events).
    """
    # Try to detect new JSON format
    try:
        data = json.loads(script)
        if isinstance(data, dict) and "blocks" in data:
            async for event in _parse_json_blocks(
                data, segment_order, segment_title, duration_seconds,
                total_segments, is_last_segment=is_last_segment,
                session_id=session_id, from_chunk=from_chunk,
                emit_terminal_events=emit_terminal_events,
                hinglish_map=hinglish_map,
            ):
                yield event
            return
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fall back to legacy text parser
    async for event in _parse_legacy_script(
        script, segment_order, segment_title, duration_seconds,
        total_segments, is_last_segment=is_last_segment,
        session_id=session_id, from_chunk=from_chunk,
        emit_terminal_events=emit_terminal_events,
    ):
        yield event


# ── NEW: JSON blocks parser ────────────────────────────────────────────────────

async def _parse_json_blocks(
    data: dict,
    segment_order: int,
    segment_title: str,
    duration_seconds: int,
    total_segments: int,
    *,
    is_last_segment: bool,
    session_id: str,
    from_chunk: int,
    emit_terminal_events: bool = True,
    hinglish_map: dict[str, str] | None = None,
) -> AsyncGenerator[str, None]:
    """Parse structured block JSON and emit the full hierarchy of SSE events."""

    chunk = 0

    # ── segment_start (always emitted — reconnect signal) ────────────
    yield _emit({
        "type": "segment_start",
        "segment_order": segment_order,
        "title": segment_title,
        "duration_seconds": duration_seconds,
        "total_segments": total_segments,
        "chunk": chunk,
    })

    blocks = data.get("blocks", [])

    for block_idx, block in enumerate(blocks):
        block_id = block.get("id", f"b{block_idx + 1}")
        block_title = block.get("title", "")

        # ── block_start ───────────────────────────────────────────────
        chunk += 1
        if chunk >= from_chunk:
            yield _emit({
                "type": "block_start",
                "blockId": block_id,
                "title": block_title,
                "chunk": chunk,
            })
        await asyncio.sleep(0)

        sections = block.get("sections", [])

        for section in sections:
            heading = section.get("heading", "")
            importance = section.get("importance", "medium")

            # ── section_start ─────────────────────────────────────────
            chunk += 1
            if chunk >= from_chunk:
                _section_evt: dict = {
                    "type": "section_start",
                    "heading": heading,
                    "importance": importance,
                    "readable_text": heading,
                    "chunk": chunk,
                }
                if hinglish_map and heading in hinglish_map:
                    _section_evt["hinglish"] = hinglish_map[heading]
                yield _emit(_section_evt)
            await asyncio.sleep(0)

            elements = section.get("elements", [])

            for element in elements:
                etype = element.get("type", "")

                # ── text ──────────────────────────────────────────────
                if etype == "text":
                    content = (element.get("value") or element.get("content") or "").strip()
                    if content:
                        chunk += 1
                        if chunk >= from_chunk:
                            _text_evt: dict = {"type": "text", "value": content, "readable_text": content, "chunk": chunk}
                            if hinglish_map and content in hinglish_map:
                                _text_evt["hinglish"] = hinglish_map[content]
                            yield _emit(_text_evt)
                            await asyncio.sleep(0)
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "pause", "duration": 350, "chunk": chunk})

                # ── list ──────────────────────────────────────────────
                elif etype == "list":
                    items = [i for i in element.get("items", []) if str(i).strip()]
                    if items:
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "list_start", "chunk": chunk})
                        for item in items:
                            item_text = str(item).strip()
                            chunk += 1
                            if chunk >= from_chunk:
                                _li_evt: dict = {"type": "list_item", "value": item_text, "readable_text": item_text, "chunk": chunk}
                                if hinglish_map and item_text in hinglish_map:
                                    _li_evt["hinglish"] = hinglish_map[item_text]
                                yield _emit(_li_evt)
                                await asyncio.sleep(0)
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "pause", "duration": 220, "chunk": chunk})
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "list_end", "chunk": chunk})

                # ── steps ─────────────────────────────────────────────
                elif etype == "steps":
                    steps = [s for s in element.get("steps", []) if str(s).strip()]
                    if steps:
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "steps_start", "chunk": chunk})
                        for step_num, step in enumerate(steps, 1):
                            step_text = str(step).strip()
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({
                                    "type": "step",
                                    "step_number": step_num,
                                    "value": step_text,
                                    "readable_text": f"Step {step_num}. {step_text}",
                                    "chunk": chunk,
                                })
                                await asyncio.sleep(0)
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "pause", "duration": 300, "chunk": chunk})
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "steps_end", "chunk": chunk})

                # ── table ─────────────────────────────────────────────
                elif etype == "table":
                    headers = element.get("headers", [])
                    rows = element.get("rows", [])
                    if headers or rows:
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "table_start", "headers": headers, "readable_text": "Here is a table. " + ", ".join(headers) + "." if headers else "", "chunk": chunk})
                        for row in rows:
                            row_text = ". ".join(
                                f"{headers[ci]}: {cell}" if ci < len(headers) else str(cell)
                                for ci, cell in enumerate(row)
                            )
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "table_row", "row": row, "readable_text": row_text, "chunk": chunk})
                                await asyncio.sleep(0)
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "pause", "duration": 200, "chunk": chunk})
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "table_end", "chunk": chunk})

                # ── accordion ─────────────────────────────────────────
                elif etype == "accordion":
                    acc_title = (element.get("title") or "").strip()
                    acc_content = (element.get("content") or "").strip()
                    if acc_title or acc_content:
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({
                                "type": "accordion",
                                "title": acc_title,
                                "content": acc_content,
                                "readable_text": f"{acc_title}. {acc_content}".strip(". "),
                                "chunk": chunk,
                            })

                # ── tabs ──────────────────────────────────────────────
                elif etype == "tabs":
                    tabs = element.get("tabs", [])
                    if tabs:
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "tabs_start", "chunk": chunk})
                        for tab in tabs:
                            tab_label = (tab.get("label") or "").strip()
                            tab_content = (tab.get("content") or "").strip()
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "tab_start", "label": tab_label, "readable_text": tab_label, "chunk": chunk})
                            if tab_content:
                                chunk += 1
                                if chunk >= from_chunk:
                                    yield _emit({"type": "text", "value": tab_content, "readable_text": tab_content, "chunk": chunk})
                                    await asyncio.sleep(0)
                            chunk += 1
                            if chunk >= from_chunk:
                                yield _emit({"type": "tab_end", "chunk": chunk})
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "tabs_end", "chunk": chunk})

                # ── question ──────────────────────────────────────────
                elif etype == "question":
                    q_text = (element.get("question") or "").strip()
                    q_opts = element.get("options", [])
                    q_ans = (element.get("answer") or "").strip()
                    if q_text:
                        opts_readable = ". ".join(
                            f"Option {i + 1}: {opt}" for i, opt in enumerate(q_opts)
                        )
                        readable = f"Here is a question. {q_text} {opts_readable}."
                        chunk += 1
                        if chunk >= from_chunk:
                            _q_evt: dict = {
                                "type": "question",
                                "question": q_text,
                                "options": q_opts,
                                "answer": q_ans,
                                "readable_text": readable,
                                "chunk": chunk,
                            }
                            if hinglish_map and readable in hinglish_map:
                                _q_evt["hinglish"] = hinglish_map[readable]
                            yield _emit(_q_evt)
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "pause", "duration": 500, "chunk": chunk})

                # ── summary ───────────────────────────────────────────
                elif etype == "summary":
                    points = [p for p in element.get("points", []) if str(p).strip()]
                    if points:
                        summary_readable = "Here is a summary. " + ". ".join(str(p).strip() for p in points) + "."
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "summary", "points": points, "readable_text": summary_readable, "chunk": chunk})
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "pause", "duration": 400, "chunk": chunk})

                # ── visual_hint ───────────────────────────────────────
                elif etype == "visual_hint":
                    hint_text = (element.get("text") or "").strip()
                    hint_image_url = element.get("image_url") or None
                    if hint_text:
                        chunk += 1
                        if chunk >= from_chunk:
                            vh_payload: dict = {
                                "type": "visual_hint",
                                "text": hint_text,
                                "image_url": hint_image_url,
                                "chunk": chunk,
                            }
                            yield _emit(vh_payload)
                        # Visual hints are image generation prompts — not spoken by TTS.
                        # The image_ready event delivers the generated image URL later.
                        chunk += 1
                        if chunk >= from_chunk:
                            yield _emit({"type": "pause", "duration": 400, "chunk": chunk})

            # ── section_end ───────────────────────────────────────────
            chunk += 1
            if chunk >= from_chunk:
                yield _emit({"type": "section_end", "chunk": chunk})
            await asyncio.sleep(0)

        # ── pause between blocks ──────────────────────────────────────
        chunk += 1
        if chunk >= from_chunk:
            yield _emit({"type": "pause", "duration": 700, "chunk": chunk})

        # ── block_end (include references + next for UI arrows) ────────
        block_references = block.get("references", [])
        block_next = block.get("next", [])
        chunk += 1
        if chunk >= from_chunk:
            yield _emit({
                "type": "block_end",
                "blockId": block_id,
                "references": block_references,
                "next": block_next,
                "chunk": chunk,
            })
        await asyncio.sleep(0)

    # ── segment_end ───────────────────────────────────────────────────
    if emit_terminal_events:
        chunk += 1
        yield _emit({"type": "segment_end", "segment_order": segment_order, "chunk": chunk})

        # ── session_end (last segment only) ──────────────────────────────
        if is_last_segment:
            chunk += 1
            yield _emit({"type": "session_end", "session_id": session_id, "chunk": chunk})


# ── LEGACY: speech-text parser (kept for backward compatibility) ──────────────

async def _parse_legacy_script(
    script: str,
    segment_order: int,
    segment_title: str,
    duration_seconds: int,
    total_segments: int,
    *,
    is_last_segment: bool,
    session_id: str,
    from_chunk: int,
    emit_terminal_events: bool = True,
) -> AsyncGenerator[str, None]:
    """Parse a speech-first text script and emit legacy-format SSE events."""

    chunk = 0

    # chunk 0 — segment_start, always emitted
    yield _emit({
        "type": "segment_start",
        "segment_order": segment_order,
        "title": segment_title,
        "duration_seconds": duration_seconds,
        "total_segments": total_segments,
        "chunk": chunk,
    })

    current_emotion = "neutral"
    wb_counter = 0

    for match in _TOKEN_RE.finditer(script):
        animation, pause, emotion_tag, sentence, fallback = match.groups()

        if animation:
            chunk += 1
            wb_counter += 1
            wb_id = f"wb_{segment_order}_{wb_counter}"
            type_match = re.search(r"type\s*=\s*(\w+)", animation)
            desc_match = re.search(r"description\s*=\s*(.+?)(?=,\s*\w+=|\])", animation)
            if chunk >= from_chunk:
                yield _emit({
                    "type": "whiteboard",
                    "action": "draw",
                    "content_type": type_match.group(1) if type_match else "diagram",
                    "description": desc_match.group(1).strip() if desc_match else animation,
                    "id": wb_id,
                    "chunk": chunk,
                })

        elif pause:
            chunk += 1
            ms_raw = re.search(r"(\d+(?:\.\d+)?)", pause)
            ms = int(float(ms_raw.group(1))) if ms_raw else 300
            if chunk >= from_chunk:
                yield _emit({"type": "pause", "duration": ms, "chunk": chunk})

        elif emotion_tag:
            value = emotion_tag.strip("[]").lower()
            if value in VALID_EMOTIONS:
                current_emotion = value
                chunk += 1
                if chunk >= from_chunk:
                    yield _emit({"type": "emotion", "value": current_emotion, "chunk": chunk})

        elif sentence and sentence.strip():
            clean = sentence.strip()
            if len(clean) > 1 and not clean.startswith("[") and not clean.startswith("<"):
                chunk += 1
                if chunk >= from_chunk:
                    yield _emit({"type": "text", "value": clean, "chunk": chunk})
                    await asyncio.sleep(0)

        elif fallback and fallback.strip():
            clean = fallback.strip()
            if len(clean) > 1 and not clean.startswith("[") and not clean.startswith("<"):
                wb_bare = re.match(
                    r"^WHITEBOARD:\s*action\s*=\s*(\w+)\s*,\s*content\s*=\s*(.+)$",
                    clean,
                    re.IGNORECASE,
                )
                if wb_bare:
                    chunk += 1
                    wb_counter += 1
                    wb_id = f"wb_{segment_order}_{wb_counter}"
                    if chunk >= from_chunk:
                        yield _emit({
                            "type": "whiteboard",
                            "action": wb_bare.group(1).lower(),
                            "content_type": "text",
                            "description": wb_bare.group(2).strip(),
                            "id": wb_id,
                            "chunk": chunk,
                        })
                else:
                    chunk += 1
                    if chunk >= from_chunk:
                        yield _emit({"type": "text", "value": clean, "chunk": chunk})
                        await asyncio.sleep(0)

    # segment_end
    if emit_terminal_events:
        chunk += 1
        yield _emit({"type": "segment_end", "segment_order": segment_order, "chunk": chunk})

        if is_last_segment:
            chunk += 1
            yield _emit({"type": "session_end", "session_id": session_id, "chunk": chunk})

