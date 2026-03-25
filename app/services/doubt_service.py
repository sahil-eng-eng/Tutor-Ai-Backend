"""
Doubt Service — handles hand raises, doubt submissions, OCR doubts, and resolution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.interaction import DoubtRecord, Interaction, InteractionType
from app.models.session import TutorSession, SessionSegment, SegmentStatus
from app.prompts.interaction_prompts import (
    DOUBT_ACKNOWLEDGEMENT_RESPONSES,
    DOUBT_RESOLVED_RESPONSES,
    get_random_response,
)
from app.prompts.prompt_composer import compose_doubt_resolution_prompt, compose_live_doubt_prompt
from app.schemas.interaction import DoubtResponse
from app.services.ai_tutor_service import chat_completion, streaming_chat_completion
from app.services.model_selector_service import get_model_for_doubt_resolution
from app.services.ocr_service import extract_text_from_image

logger = logging.getLogger("ai_tutor")

# Sentence-boundary regex: end of sentence punctuation followed by whitespace or string-end
_SENTENCE_END_RE = re.compile(r"[.!?…](?:\s|$)")


def _emit_text_chunks(
    text: str,
    sse_fn,
    sentence_re: re.Pattern,
):
    """Synchronous generator — splits *text* on sentence boundaries and yields
    SSE-formatted strings, finishing with a ``doubt_end`` event."""
    buffer = text
    chunk_idx = 0
    while buffer:
        m = sentence_re.search(buffer)
        if not m:
            break
        end = m.end()
        sentence = buffer[:end].strip()
        buffer = buffer[end:]
        if sentence:
            chunk_idx += 1
            yield sse_fn({"type": "text", "value": sentence, "chunk": chunk_idx})

    # Flush any trailing text that didn't end with punctuation
    if buffer.strip():
        chunk_idx += 1
        yield sse_fn({"type": "text", "value": buffer.strip(), "chunk": chunk_idx})

    yield sse_fn({"type": "doubt_end", "chunk": chunk_idx + 1})


class DoubtService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def hand_raise(
        self, session_id: UUID, user_id: UUID, timestamp_seconds: Optional[int] = None
    ) -> dict:
        """Handle student hand-raise — pause session and acknowledge."""
        session = await self._get_session(session_id, user_id)

        ack_message = get_random_response(DOUBT_ACKNOWLEDGEMENT_RESPONSES)

        interaction = Interaction(
            session_id=session_id,
            interaction_type=InteractionType.HAND_RAISE,
            ai_response=ack_message,
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(interaction)
        await self._db.flush()

        return {
            "status": "paused_for_doubt",
            "acknowledgement": ack_message,
            "interaction_id": str(interaction.id),
        }

    async def submit_doubt(
        self,
        session_id: UUID,
        user_id: UUID,
        doubt_text: Optional[str] = None,
        doubt_image_path: Optional[str] = None,
        timestamp_seconds: Optional[int] = None,
    ) -> DoubtResponse:
        """Submit a doubt (text or image) and get AI resolution."""
        session = await self._get_session(session_id, user_id)

        # Determine current topic from active segment
        current_topic = session.concept_name
        active_segments = [
            s for s in session.segments
            if s.status.value in ("in_progress", "pending")
        ]
        if active_segments:
            current_topic = active_segments[0].title

        # OCR if image provided
        ocr_text = None
        if doubt_image_path:
            try:
                ocr_text = await extract_text_from_image(doubt_image_path)
            except Exception:
                logger.exception("OCR extraction failed")

        # Build the doubt prompt
        combined_doubt = doubt_text or ""
        if ocr_text:
            combined_doubt += f"\n[From uploaded image]: {ocr_text}"

        if not combined_doubt.strip():
            raise BadRequestException("Doubt text or image required")

        # Get AI response
        doubt_prompt = compose_doubt_resolution_prompt(
            doubt_text=combined_doubt,
            study_level=session.study_level.value,
            current_topic=current_topic,
            ocr_text=ocr_text,
        )

        try:
            ai_response = await chat_completion(
                system_prompt=session.system_prompt_snapshot or "",
                user_message=doubt_prompt,
                model=get_model_for_doubt_resolution(session.study_level.value),
                temperature=0.6,
            )
        except Exception:
            logger.exception("AI doubt resolution failed")
            ai_response = (
                "I understand your doubt. Let me try to explain this differently. "
                "Could you tell me specifically which part is confusing?"
            )

        # Store doubt
        doubt = DoubtRecord(
            session_id=session_id,
            doubt_text=doubt_text,
            doubt_image_path=doubt_image_path,
            ocr_extracted_text=ocr_text,
            ai_response=ai_response,
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(doubt)

        # Store interaction
        interaction = Interaction(
            session_id=session_id,
            interaction_type=InteractionType.DOUBT,
            user_message=combined_doubt,
            ai_response=ai_response,
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(interaction)
        await self._db.flush()

        return DoubtResponse.model_validate(doubt)

    async def resolve_doubt(
        self,
        doubt_id: UUID,
        session_id: UUID,
        user_id: UUID,
        resolution_method: str = "go_ahead_button",
        user_message: Optional[str] = None,
    ) -> dict:
        """Mark a doubt as resolved and resume session."""
        await self._get_session(session_id, user_id)

        result = await self._db.execute(
            select(DoubtRecord).where(
                DoubtRecord.id == doubt_id,
                DoubtRecord.session_id == session_id,
            )
        )
        doubt = result.scalar_one_or_none()
        if not doubt:
            raise NotFoundException("Doubt not found")

        doubt.is_resolved = True
        doubt.resolution_method = resolution_method

        resume_message = get_random_response(DOUBT_RESOLVED_RESPONSES)

        interaction = Interaction(
            session_id=session_id,
            interaction_type=InteractionType.DOUBT,
            user_message=user_message or f"Doubt resolved via {resolution_method}",
            ai_response=resume_message,
            metadata_json={"doubt_id": str(doubt_id), "resolution": resolution_method},
        )
        self._db.add(interaction)
        await self._db.flush()

        return {
            "status": "resolved",
            "resume_message": resume_message,
            "doubt_id": str(doubt_id),
        }

    async def list_doubts(
        self, session_id: UUID, user_id: UUID
    ) -> list[DoubtResponse]:
        await self._get_session(session_id, user_id)
        result = await self._db.execute(
            select(DoubtRecord)
            .where(DoubtRecord.session_id == session_id)
            .order_by(DoubtRecord.created_at)
        )
        doubts = result.scalars().all()
        return [DoubtResponse.model_validate(d) for d in doubts]

    # ── Internal ───────────────────────────────────────────────────────

    async def stream_live_doubt(
        self,
        session_id: UUID,
        user_id: UUID,
        query_text: str,
        segment_order: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream an AI answer to a live doubt raised during segment playback.

        Yields SSE-formatted strings:
          doubt_start → text (×N sentences) → doubt_end

        The active segment's content_script (first 2000 chars) is passed as
        context so the AI grounds its answer in what was just taught.
        """
        # Load session with segments
        result = await self._db.execute(
            select(TutorSession)
            .where(TutorSession.id == session_id, TutorSession.user_id == user_id)
            .options(selectinload(TutorSession.segments))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException("Session not found")

        # Identify context segment
        context_seg: Optional[SessionSegment] = None
        if segment_order is not None:
            for seg in session.segments:
                if seg.segment_order == segment_order:
                    context_seg = seg
                    break
        if context_seg is None:
            for seg in session.segments:
                if seg.status == SegmentStatus.IN_PROGRESS:
                    context_seg = seg
                    break

        # Build context string
        segment_ctx = ""
        if context_seg and context_seg.content_script:
            segment_ctx = (
                f"\n\nCurrent segment being taught: \"{context_seg.title}\"\n"
                f"Segment content (excerpt):\n{context_seg.content_script[:2000]}"
            )

        system_prompt = (
            session.system_prompt_snapshot or
            "You are an expert AI tutor. Answer student doubts clearly and concisely."
        )
        user_message = compose_live_doubt_prompt(
            query_text=query_text,
            concept_name=session.concept_name,
            segment_ctx=segment_ctx,
        )

        def _sse(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        yield _sse({"type": "doubt_start", "query": query_text})

        # Buffer the complete response so we can detect MCQ vs plain-text.
        # MCQ responses are short, and text responses are assembled quickly,
        # so the extra latency is negligible.
        full_answer = ""
        try:
            async for token in streaming_chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                model=session.ai_model_used or "gpt-4o-mini",
                temperature=0.6,
                max_tokens=1024,
            ):
                full_answer += token
                await asyncio.sleep(0)  # yield control while accumulating

        except Exception:
            logger.exception("Live doubt streaming failed for session %s", session_id)
            yield _sse({"type": "error", "code": "stream_error", "message": "Answer stream failed"})
            return

        # ── Detect MCQ vs plain-text response ──────────────────────────
        _MCQ_START = "MCQ_START"
        _MCQ_END = "MCQ_END"

        if _MCQ_START in full_answer and _MCQ_END in full_answer:
            # Parse structured MCQ block
            try:
                start_idx = full_answer.index(_MCQ_START) + len(_MCQ_START)
                end_idx = full_answer.index(_MCQ_END)
                json_str = full_answer[start_idx:end_idx].strip()
                mcq_data = json.loads(json_str)

                # Normalise options: strip any GPT-generated label prefix (A) B. etc.)
                # then re-label A–E so duplicates are impossible.
                _opt_label_re = re.compile(r"^[A-Ea-e][\).]\s*")
                options: list = mcq_data.get("options", [])
                options = [_opt_label_re.sub("", str(o)).strip() for o in options]

                # Ensure the "Do not know" option is present
                if not any("do not know" in o.lower() for o in options):
                    options.append("Do not know")

                # Trim to 5 options and re-label A–E sequentially
                options = options[:5]
                options = [f"{chr(65 + i)}) {opt}" for i, opt in enumerate(options)]
                mcq_data["options"] = options

                # Canonicalise correct_answer to a single uppercase letter
                raw_ans = str(mcq_data.get("correct_answer", "A")).strip().upper()
                correct = raw_ans[0] if raw_ans else "A"
                if correct not in "ABCDE":
                    correct = "A"
                mcq_data["correct_answer"] = correct

                yield _sse({"type": "mcq_start"})
                yield _sse({
                    "type": "mcq_data",
                    "question": mcq_data.get("question", ""),
                    "options": mcq_data.get("options", []),
                    "correct_answer": mcq_data.get("correct_answer", ""),
                    "explanation": mcq_data.get("explanation", ""),
                })
                yield _sse({"type": "mcq_end", "chunk": 1})

            except Exception:
                logger.exception("MCQ parse failed for session %s — falling back to text", session_id)
                # Fall through to plain-text emission below
                for event_str in _emit_text_chunks(full_answer, _sse, _SENTENCE_END_RE):
                    yield event_str
        else:
            # ── Plain-text response: split into sentences and emit ──────
            for event_str in _emit_text_chunks(full_answer, _sse, _SENTENCE_END_RE):
                yield event_str

        # Store interaction record
        try:
            interaction = Interaction(
                session_id=session_id,
                interaction_type=InteractionType.DOUBT,
                user_message=query_text,
                ai_response=full_answer,
                metadata_json={
                    "live_stream": True,
                    "segment_order": segment_order or (context_seg.segment_order if context_seg else None),
                },
            )
            self._db.add(interaction)
            await self._db.flush()
        except Exception:
            logger.exception("Failed to store live doubt interaction for session %s", session_id)

    async def _get_session(self, session_id: UUID, user_id: UUID) -> TutorSession:
        result = await self._db.execute(
            select(TutorSession).where(
                TutorSession.id == session_id,
                TutorSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException("Session not found")
        return session
