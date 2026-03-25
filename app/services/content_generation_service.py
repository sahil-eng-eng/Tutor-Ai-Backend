"""
Content Generation Service — produces animations, whiteboard data, and notes.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.content import AnimationData, WhiteboardData, SessionNotes
from app.models.session import TutorSession, SessionSegment
from app.prompts.prompt_composer import compose_notes_generation_prompt
from app.schemas.content import (
    AnimationResponse,
    WhiteboardResponse,
    SessionNotesResponse,
    SessionContentResponse,
)
from app.services.ai_tutor_service import generate_json_response
from app.services.model_selector_service import MODEL_TIERS

logger = logging.getLogger("ai_tutor")


class ContentGenerationService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def generate_session_content(
        self, session_id: UUID, user_id: UUID
    ) -> SessionContentResponse:
        """Generate all content (animations + whiteboard) for a session."""
        session = await self._get_session(session_id, user_id)
        animations = await self._generate_animations_for_session(session)
        whiteboards = await self._generate_whiteboards_for_session(session)

        return SessionContentResponse(
            session_id=session.id,
            animations=[AnimationResponse.model_validate(a) for a in animations],
            whiteboards=[WhiteboardResponse.model_validate(w) for w in whiteboards],
        )

    async def get_session_content(
        self, session_id: UUID, user_id: UUID
    ) -> SessionContentResponse:
        """Retrieve existing content for a session."""
        session = await self._get_session(session_id, user_id)

        anim_result = await self._db.execute(
            select(AnimationData).where(AnimationData.session_id == session_id)
        )
        animations = anim_result.scalars().all()

        wb_result = await self._db.execute(
            select(WhiteboardData).where(WhiteboardData.session_id == session_id)
        )
        whiteboards = wb_result.scalars().all()

        notes_result = await self._db.execute(
            select(SessionNotes).where(SessionNotes.session_id == session_id)
        )
        notes = notes_result.scalar_one_or_none()

        return SessionContentResponse(
            session_id=session_id,
            animations=[AnimationResponse.model_validate(a) for a in animations],
            whiteboards=[WhiteboardResponse.model_validate(w) for w in whiteboards],
            notes=SessionNotesResponse.model_validate(notes) if notes else None,
        )

    async def generate_notes(
        self, session_id: UUID, user_id: UUID
    ) -> SessionNotesResponse:
        """Generate study notes for a completed session."""
        session = await self._get_session(session_id, user_id)

        # Collect segment content
        segments_content = "\n\n".join(
            f"## {seg.title}\n{seg.content_script or ''}"
            for seg in sorted(session.segments, key=lambda s: s.segment_order)
            if seg.content_script
        )

        prompt = compose_notes_generation_prompt(segments_content, session.concept_name)

        try:
            result = await generate_json_response(
                system_prompt="You are a study notes generator. Return valid JSON.",
                user_message=prompt,
                model=MODEL_TIERS["cheap"],
                max_tokens=8192,
            )

            if isinstance(result, dict):
                content_md = result.get("content_markdown", "")
                key_points = result.get("key_points", [])
                formulas = result.get("formulas", [])
                diagrams = result.get("diagrams", [])
            else:
                content_md = str(result)
                key_points, formulas, diagrams = [], [], []
        except Exception:
            logger.exception("Failed to generate notes via AI")
            content_md = segments_content
            key_points, formulas, diagrams = [], [], []

        # Upsert notes
        existing = await self._db.execute(
            select(SessionNotes).where(SessionNotes.session_id == session_id)
        )
        notes = existing.scalar_one_or_none()
        if notes:
            notes.content_markdown = content_md
            notes.key_points = key_points
            notes.formulas = formulas
            notes.diagrams = diagrams
            notes.generated_at = datetime.now(timezone.utc)
        else:
            notes = SessionNotes(
                session_id=session_id,
                content_markdown=content_md,
                key_points=key_points,
                formulas=formulas,
                diagrams=diagrams,
                generated_at=datetime.now(timezone.utc),
            )
            self._db.add(notes)

        await self._db.flush()
        return SessionNotesResponse.model_validate(notes)

    # ── Internal ───────────────────────────────────────────────────────

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

    async def _generate_animations_for_session(
        self, session: TutorSession
    ) -> list[AnimationData]:
        """Generate animation specs for segments that have animation cues."""
        animations = []
        cumulative_seconds = 0

        for segment in sorted(session.segments, key=lambda s: s.segment_order):
            if segment.animation_cues:
                cues = segment.animation_cues
                anim = AnimationData(
                    session_id=session.id,
                    segment_id=segment.id,
                    animation_type=cues.get("type", "diagram"),
                    title=cues.get("title", segment.title),
                    description=cues.get("description", ""),
                    animation_spec=cues,
                    trigger_timestamp_seconds=cumulative_seconds,
                    duration_seconds=cues.get("duration_seconds", 30),
                    sync_text=cues.get("sync_text"),
                )
                self._db.add(anim)
                animations.append(anim)

            cumulative_seconds += segment.duration_seconds or 0

        await self._db.flush()
        return animations

    async def _generate_whiteboards_for_session(
        self, session: TutorSession
    ) -> list[WhiteboardData]:
        """Generate whiteboard specs for segments that have whiteboard cues."""
        whiteboards = []
        cumulative_seconds = 0

        for segment in sorted(session.segments, key=lambda s: s.segment_order):
            if segment.whiteboard_cues:
                cues = segment.whiteboard_cues
                wb = WhiteboardData(
                    session_id=session.id,
                    segment_id=segment.id,
                    title=cues.get("title", segment.title),
                    content_type=cues.get("content_type", "text"),
                    whiteboard_spec=cues,
                    trigger_timestamp_seconds=cumulative_seconds,
                    sync_text=cues.get("sync_text"),
                )
                self._db.add(wb)
                whiteboards.append(wb)

            cumulative_seconds += segment.duration_seconds or 0

        await self._db.flush()
        return whiteboards
