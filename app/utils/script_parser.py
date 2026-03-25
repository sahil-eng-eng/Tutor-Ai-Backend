"""
parse_script_to_sse_events — converts a saved content_script into structured SSE data events.

Script markup conventions handled:
  [warm], [curious], [calm], [excited], [serious], [friendly]  → emotion events
  <pause:400ms>                                                 → pause events
  [ANIMATION: type=X, description=Y]                           → whiteboard events
  Plain sentences (ending with . ! ? … or line-end)            → text events
"""

import asyncio
import json
import re
from typing import AsyncGenerator


def _emit(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


VALID_EMOTIONS = {"warm", "curious", "calm", "excited", "serious", "friendly", "neutral"}

# Matches (in order of precedence):
#   1. [ANIMATION: ...] block
#   2. <pause:Xms> marker
#   3. [emotion_tag] (single word in brackets)
#   4. A sentence ending with punctuation (.!?…)
#   5. Fallback: non-empty text run (no punctuation end)
#
# Each alternative starts with a non-whitespace anchor so finditer()
# naturally skips whitespace between tokens.
_TOKEN_RE = re.compile(
    r"(\[ANIMATION:[^\]]*\])"                  # group 1: animation block
    r"|(<pause:\d+(?:\.\d+)?ms>)"              # group 2: pause marker
    r"|(\[[a-zA-Z_]+\])"                       # group 3: potential emotion tag
    r"|([^<\[\]\s][^<\[\]\n]*?[.!?…])"         # group 4: sentence (lazy, ends at first punct)
    r"|([^<\[\]\s][^<\[\]\n]*)",               # group 5: fallback text run
    re.MULTILINE,
)


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
) -> AsyncGenerator[str, None]:
    """
    Parse a saved content_script and yield fully-formatted SSE ``data: {...}\\n\\n`` strings.

    Yields ``segment_start`` first (chunk 0, always), then one event per parsed token,
    then ``segment_end``.  If *is_last_segment* is True, a ``session_end`` event follows.

    *from_chunk* allows resuming mid-stream: events with ``chunk < from_chunk`` are skipped.
    ``segment_start`` (chunk 0) is always emitted so the frontend can confirm the stream
    reconnected.  Content events start at chunk 1.
    """
    # chunk 0 — segment_start, always emitted (signals successful reconnect)
    chunk = 0
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
                # Route bare "WHITEBOARD: action=X, content=Y" lines to whiteboard events
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
    chunk += 1
    yield _emit({
        "type": "segment_end",
        "segment_order": segment_order,
        "chunk": chunk,
    })

    # session_end — only after the very last segment
    if is_last_segment:
        chunk += 1
        yield _emit({
            "type": "session_end",
            "session_id": session_id,
            "chunk": chunk,
        })
