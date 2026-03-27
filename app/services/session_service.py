"""
Session Service — manages session lifecycle, AI evaluation, segment generation,
real-time teaching, and session end management.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
)
from app.models.session import (
    DurationType,
    EntireSessionType,
    SessionConfig,
    SessionMode,
    SessionPlaylist,
    SessionSegment,
    SessionStatus,
    SegmentStatus,
    StudyLevel,
    TutorSession,
)
from app.models.cache import SessionCache
from app.models.user import User
from app.models.material import UserMaterial
from app.models.voice import VoiceProfile
from app.models.curriculum import Board, Subject, Chapter
from app.prompts.prompt_composer import (
    compose_system_prompt,
    compose_segment_plan_prompt,
    compose_segment_content_prompt,
    compose_session_evaluation_prompt,
    compose_session_goodbye_prompt,
    compose_session_teaching_prompt,
    compose_structured_teaching_system_prompt,
    calculate_target_wpm,
)
from app.schemas.session import (
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionPreviewResponse,
    SessionResponse,
    SessionUpdate,
    PlaylistResponse,
)
from app.services.model_selector_service import select_model
from app.services.ai_tutor_service import (
    generate_json_response,
    chat_completion,
    streaming_chat_completion,
)

logger = logging.getLogger("ai_tutor")

# ── Prefetch tuning ────────────────────────────────────────────────────
_PREFETCH_MAX_WAIT = 15.0  # max seconds to wait for a background prefetch
_PREV_CONTEXT_CHARS = 800  # chars of previous segment script passed to AI


async def _background_prefetch_segment(
    session_id: UUID, user_id: UUID, segment_order: int
) -> None:
    """Background ``asyncio.Task``: generate ``content_script`` for a future segment.

    Uses an **independent** DB session so it can run concurrently with the
    request-scoped session that is streaming the current segment.  The
    generated script is committed to the database; the SSE endpoint for the
    next segment will pick it up via :py:meth:`SessionService._wait_for_content_script`.
    """
    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            service = SessionService(db)
            session = await service._get_session_or_404(session_id, user_id)

            target = None
            for seg in session.segments:
                if seg.segment_order == segment_order:
                    target = seg
                    break

            if not target or target.content_script:
                return  # already generated or segment doesn't exist

            prev_summary = service._get_previous_segment_summary(session, segment_order)
            material_summary = await service._get_material_summary(session)
            eval_seg = service._find_eval_segment(session, segment_order)

            if not eval_seg:
                logger.warning(
                    "No evaluation data for segment %d — skipping prefetch", segment_order
                )
                return

            content = await service._generate_segment_script(
                session, eval_seg, segment_order, prev_summary, material_summary
            )

            # Re-check: if config changed while we were generating,
            # the segment's content_script may have been invalidated (set to None).
            # Only write if it's still None to avoid overwriting a newer generation.
            await db.refresh(target)
            if target.content_script:
                logger.info("Segment %d already has content — discarding prefetch", segment_order)
                return

            target.content_script = content
            await db.commit()
            logger.info(
                "Prefetch complete: segment %d ready (%d chars)", segment_order, len(content)
            )
    except Exception:
        logger.exception(
            "Background prefetch failed for segment %d of session %s",
            segment_order, session_id,
        )


class SessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Create Session ─────────────────────────────────────────────────

    async def create_session(
        self, user: User, data: SessionCreate
    ) -> SessionDetailResponse:
        """Create a session, run AI evaluation, store session_evaluation JSON."""

        # Determine AI model
        ai_model = select_model(
            study_level=data.study_level.value,
            session_type=data.entire_session_type.value,
        )

        # Resolve voice profile tutor name
        tutor_name = "Arjun"
        if data.voice_id:
            vp_result = await self._db.execute(
                select(VoiceProfile).where(VoiceProfile.id == data.voice_id)
            )
            voice = vp_result.scalar_one_or_none()
            if voice:
                tutor_name = voice.tutor_name

        # Resolve duration
        duration_minutes = data.duration_minutes
        if data.duration_type == DurationType.AI_DETERMINED:
            duration_minutes = self._estimate_duration(
                data.entire_session_type, data.study_level
            )
        if duration_minutes and duration_minutes > settings.MAX_SESSION_DURATION_MINUTES:
            duration_minutes = settings.MAX_SESSION_DURATION_MINUTES

        # Gather user material summaries
        user_material_summary = None
        if data.material_ids:
            mat_result = await self._db.execute(
                select(UserMaterial).where(
                    UserMaterial.id.in_(data.material_ids),
                    UserMaterial.user_id == user.id,
                )
            )
            materials = mat_result.scalars().all()
            summaries = [
                m.extracted_content[:2000]
                for m in materials
                if m.extracted_content and not m.extracted_content.startswith("[")
            ]
            if summaries:
                user_material_summary = "\n---\n".join(summaries)

        # Resolve curriculum names for evaluation prompt
        board_name = subject_name = chapter_name = None
        if data.board_id:
            b = await self._db.execute(select(Board).where(Board.id == data.board_id))
            board_obj = b.scalar_one_or_none()
            if board_obj:
                board_name = board_obj.name
        if data.subject_id:
            s = await self._db.execute(select(Subject).where(Subject.id == data.subject_id))
            subj_obj = s.scalar_one_or_none()
            if subj_obj:
                subject_name = subj_obj.name
        if data.chapter_id:
            c = await self._db.execute(select(Chapter).where(Chapter.id == data.chapter_id))
            ch_obj = c.scalar_one_or_none()
            if ch_obj:
                chapter_name = ch_obj.name

        # ── AI Evaluation: generate session_evaluation JSON ────────
        eval_prompt = compose_session_evaluation_prompt(
            user_profession=data.user_profession.value,
            concept_name=data.concept_name,
            description=data.description,
            study_level=data.study_level.value,
            entire_session_type=data.entire_session_type.value,
            mood=data.mood.value,
            personality=data.model_personality.value,
            language=data.language,
            duration_type=data.duration_type.value,
            duration_minutes=duration_minutes,
            board_name=board_name,
            class_name=data.class_name,
            subject_name=subject_name,
            chapter_name=chapter_name,
            university=data.university,
            course=data.course,
            semester=data.semester,
            professional_background=data.professional_background,
            user_material_summary=user_material_summary,
        )

        try:
            session_evaluation = await generate_json_response(
                system_prompt="You are a curriculum design AI. Return valid JSON only.",
                user_message=eval_prompt,
                model=ai_model,
                temperature=0.5,
                max_tokens=8192,
            )
        except Exception:
            logger.exception("AI evaluation failed, using fallback")
            session_evaluation = self._fallback_evaluation(
                data.concept_name, duration_minutes or 60
            )

        # Compose system prompt for later teaching use
        system_prompt = compose_system_prompt(
            tutor_name=tutor_name,
            language=data.language,
            user_type=user.user_type.value,
            age=user.age,
            grade=user.grade,
            institution=user.institution,
            board=user.board,
            concept_name=data.concept_name,
            description=data.description,
            study_level=data.study_level.value,
            entire_session_type=data.entire_session_type.value,
            mood=data.mood.value,
            personality=data.model_personality.value,
            duration_type=data.duration_type.value,
            duration_minutes=duration_minutes,
            session_mode=data.session_mode.value,
            user_material_summary=user_material_summary,
        )

        # Handle playlist for multiple sessions
        playlist = None
        if data.session_mode == SessionMode.MULTIPLE_SESSIONS:
            playlist = SessionPlaylist(
                user_id=user.id,
                title=f"Playlist: {data.concept_name}",
                concept_name=data.concept_name,
            )
            self._db.add(playlist)
            await self._db.flush()

        # Extract evaluation total duration
        eval_duration = None
        if isinstance(session_evaluation, dict):
            overview = session_evaluation.get("session_overview", {})
            eval_duration = overview.get("estimated_total_duration_seconds")

        # Create session
        session = TutorSession(
            user_id=user.id,
            playlist_id=playlist.id if playlist else None,
            playlist_order=1 if playlist else None,
            user_profession=data.user_profession.value,
            concept_name=data.concept_name,
            description=data.description,
            mood=data.mood,
            model_personality=data.model_personality,
            language=data.language,
            duration_type=data.duration_type,
            duration_minutes=duration_minutes,
            voice_id=data.voice_id,
            session_mode=data.session_mode,
            study_level=data.study_level,
            entire_session_type=data.entire_session_type,
            status=SessionStatus.DRAFT,
            ai_model_used=ai_model,
            system_prompt_snapshot=system_prompt,
            session_evaluation=session_evaluation,
            board_id=data.board_id,
            subject_id=data.subject_id,
            chapter_id=data.chapter_id,
            topic_id=data.topic_id,
            university=data.university,
            course=data.course,
            semester=data.semester,
            professional_background=data.professional_background,
            total_duration_seconds=eval_duration,
        )
        self._db.add(session)
        await self._db.flush()

        # Create mutable config
        config = SessionConfig(
            session_id=session.id,
            mood=data.mood.value,
            personality=data.model_personality.value,
            study_level=data.study_level.value,
            language=data.language,
            voice_id=str(data.voice_id) if data.voice_id else None,
        )
        self._db.add(config)

        # Link materials to session
        if data.material_ids:
            mat_q = await self._db.execute(
                select(UserMaterial).where(
                    UserMaterial.id.in_(data.material_ids),
                    UserMaterial.user_id == user.id,
                )
            )
            for mat in mat_q.scalars().all():
                mat.session_id = session.id

        await self._db.flush()

        refreshed = await self._get_session_or_404(session.id, session.user_id)
        return SessionDetailResponse.model_validate(refreshed)

    # ── Preview Session ────────────────────────────────────────────────

    async def preview_session(
        self, session_id: UUID, user_id: UUID
    ) -> SessionPreviewResponse:
        """Return session_evaluation data for frontend preview."""
        session = await self._get_session_or_404(session_id, user_id)
        return SessionPreviewResponse(
            session_id=session.id,
            concept_name=session.concept_name,
            description=session.description,
            user_profession=session.user_profession,
            status=session.status,
            session_evaluation=session.session_evaluation,
            total_duration_seconds=session.total_duration_seconds,
        )

    # ── Update Session Evaluation ──────────────────────────────────────

    async def update_session_evaluation(
        self, session_id: UUID, user_id: UUID, updated_eval: dict
    ) -> SessionPreviewResponse:
        """Frontend sends back modified session_evaluation after preview editing."""
        session = await self._get_session_or_404(session_id, user_id)
        if session.status not in (SessionStatus.DRAFT, SessionStatus.READY):
            raise BadRequestException(
                "Cannot update evaluation after session has started"
            )
        session.session_evaluation = updated_eval

        # Recalculate total duration from updated segments
        segments = updated_eval.get("segments", [])
        total_secs = sum(seg.get("duration_seconds", 0) for seg in segments)
        if total_secs:
            session.total_duration_seconds = total_secs

        await self._db.flush()
        return SessionPreviewResponse(
            session_id=session.id,
            concept_name=session.concept_name,
            description=session.description,
            user_profession=session.user_profession,
            status=session.status,
            session_evaluation=session.session_evaluation,
            total_duration_seconds=session.total_duration_seconds,
        )

    # ── Start Session ──────────────────────────────────────────────────

    async def start_session(
        self, session_id: UUID, user_id: UUID
    ) -> SessionDetailResponse:
        """Transition session to IN_PROGRESS, build segments from session_evaluation,
        and generate content for the first segment only (lazy generation)."""

        session = await self._get_session_or_404(session_id, user_id)
        if session.status not in (SessionStatus.DRAFT, SessionStatus.READY, SessionStatus.PAUSED):
            raise BadRequestException(
                f"Cannot start session in {session.status.value} state"
            )

        # If resuming from PAUSED, just update status
        if session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.IN_PROGRESS
            await self._db.flush()
            refreshed = await self._get_session_or_404(session.id, session.user_id)
            return SessionDetailResponse.model_validate(refreshed)

        # Build segment rows from session_evaluation
        evaluation = session.session_evaluation or {}
        eval_segments = evaluation.get("segments", [])

        if not eval_segments:
            eval_segments = self._fallback_evaluation(
                session.concept_name, session.duration_minutes or 60
            ).get("segments", [])

        # Gather material summary for segment content generation
        material_summary = await self._get_material_summary(session)

        # Create segment DB rows + generate content for segment 1
        segments = []
        for seg_data in eval_segments:
            order = seg_data.get("segment_order", len(segments) + 1)
            segment = SessionSegment(
                session_id=session.id,
                segment_order=order,
                segment_type=seg_data.get("segment_type", "core_teaching"),
                title=seg_data.get("title", f"Segment {order}"),
                teaching_notes=seg_data.get("teaching_approach", seg_data.get("teaching_notes")),
                duration_seconds=seg_data.get("duration_seconds", 300),
                key_points=seg_data.get("key_points"),
            )
            # Generate content only for segment 1
            if order == 1:
                segment.content_script = await self._generate_segment_script(
                    session, seg_data, order, None, material_summary
                )
                segment.status = SegmentStatus.PENDING
            self._db.add(segment)
            segments.append(segment)

        session.status = SessionStatus.IN_PROGRESS
        session.started_at = datetime.now(timezone.utc)
        session.total_duration_seconds = sum(
            s.duration_seconds or 0 for s in segments
        )

        # Recompose system prompt with full context
        session.system_prompt_snapshot = self._recompose_system_prompt(session)

        await self._db.flush()

        # Manually set the segments relationship so it's available without re-query
        # (avoids stale identity-map issue with selectinload after flush)
        session.segments = segments
        return SessionDetailResponse.model_validate(session)

    # ── Real-Time Teaching Stream (SSE) ────────────────────────────────

    async def stream_segment_teaching(
        self, session_id: UUID, user_id: UUID, segment_order: int,
        from_chunk: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Stream a segment's content_script as structured SSE events.

        Flow:
        1. If content_script is not ready (background prefetch still running),
           polls the DB for up to ``_PREFETCH_MAX_WAIT`` seconds.
        2. If still missing, generates synchronously (fallback).
        3. Immediately fires a background ``asyncio.Task`` to generate
           content_script for segment N+1 (look-ahead prefetch).
        4. Streams the script via ``parse_script_to_sse_events`` which emits
           ``segment_start``, content events, ``segment_end``, and
           ``session_end`` (last segment only).
        """
        from app.utils.script_parser import parse_script_to_sse_events

        session = await self._get_session_or_404(session_id, user_id)

        if session.status != SessionStatus.IN_PROGRESS:
            raise BadRequestException("Session is not in progress")

        # Locate the DB segment record
        target_seg = None
        for seg in session.segments:
            if seg.segment_order == segment_order:
                target_seg = seg
                break

        if not target_seg:
            raise NotFoundException(f"Segment {segment_order} not found")

        total_segments = len(session.segments)
        is_last_segment = segment_order >= total_segments

        # ── Ensure content_script is ready ──────────────────────────
        if not target_seg.content_script:
            content = await self._wait_for_content_script(
                session.id, segment_order, timeout=_PREFETCH_MAX_WAIT
            )
            if content:
                target_seg.content_script = content
            else:
                # Background prefetch didn't finish in time — generate now
                logger.info(
                    "Sync fallback: generating segment %d for session %s",
                    segment_order, session_id,
                )
                prev_summary = self._get_previous_segment_summary(session, segment_order)
                material_summary = await self._get_material_summary(session)
                eval_seg = self._find_eval_segment(session, segment_order)
                if eval_seg:
                    target_seg.content_script = await self._generate_segment_script(
                        session, eval_seg, segment_order, prev_summary, material_summary
                    )
                else:
                    target_seg.content_script = (
                        f"[warm] Let's continue with {target_seg.title}. "
                        f"<pause:300ms> We'll cover: "
                        f"{', '.join(target_seg.key_points or ['the key concepts'])}."
                    )
            await self._db.flush()

        # ── Fire N+1 background prefetch ────────────────────────────
        if not is_last_segment:
            next_seg = None
            for seg in session.segments:
                if seg.segment_order == segment_order + 1:
                    next_seg = seg
                    break
            if next_seg and not next_seg.content_script:
                asyncio.create_task(
                    _background_prefetch_segment(session.id, user_id, segment_order + 1)
                )

        # ── Mark segment in-progress (idempotent for resume) ────────
        if target_seg.status != SegmentStatus.IN_PROGRESS:
            target_seg.status = SegmentStatus.IN_PROGRESS
            target_seg.started_at = datetime.now(timezone.utc)
            await self._db.flush()

        # ── Stream the saved script as structured SSE events ────────
        async for event_str in parse_script_to_sse_events(
            script=target_seg.content_script,
            segment_order=segment_order,
            segment_title=target_seg.title or f"Segment {segment_order}",
            duration_seconds=target_seg.duration_seconds or 0,
            total_segments=total_segments,
            is_last_segment=is_last_segment,
            session_id=str(session.id),
            from_chunk=from_chunk,
        ):
            yield event_str

        # ── Mark segment complete ───────────────────────────────────
        target_seg.status = SegmentStatus.COMPLETED
        target_seg.completed_at = datetime.now(timezone.utc)
        await self._db.flush()

    # ── End Session (Manual) ───────────────────────────────────────────

    async def end_session(
        self, session_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """End session manually. Generate a humanly goodbye message."""
        session = await self._get_session_or_404(session_id, user_id)
        if session.status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED):
            raise BadRequestException("Session already ended")

        goodbye = await self._generate_goodbye(session)

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        completed_count = sum(
            1 for s in session.segments if s.status == SegmentStatus.COMPLETED
        )
        total = len(session.segments)
        session.completion_percentage = (completed_count / total * 100) if total else 100.0
        await self._db.flush()

        return {
            "session_id": str(session.id),
            "status": session.status.value,
            "goodbye_message": goodbye,
            "completion_percentage": session.completion_percentage,
        }

    # ── Auto-End Session (Called when duration/segments complete) ───────

    async def auto_end_session(
        self, session_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """Automatically end session when all segments are done or duration exceeded.
        Generates a goodbye message before completing."""
        session = await self._get_session_or_404(session_id, user_id)
        if session.status != SessionStatus.IN_PROGRESS:
            return {"session_id": str(session.id), "status": session.status.value}

        goodbye = await self._generate_goodbye(session)

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.completion_percentage = 100.0
        await self._db.flush()

        return {
            "session_id": str(session.id),
            "status": session.status.value,
            "goodbye_message": goodbye,
            "completion_percentage": 100.0,
        }

    # ── On-Demand Segment Content Generation ───────────────────────────

    async def generate_next_segment_content(
        self, session_id: UUID, user_id: UUID, segment_order: int
    ) -> SessionDetailResponse:
        """Generate content_script for a specific segment on demand."""
        session = await self._get_session_or_404(session_id, user_id)
        if session.status not in (
            SessionStatus.READY,
            SessionStatus.IN_PROGRESS,
            SessionStatus.PAUSED,
        ):
            raise BadRequestException(
                f"Cannot generate content for session in {session.status.value} state"
            )

        target = None
        for seg in session.segments:
            if seg.segment_order == segment_order:
                target = seg
                break
        if not target:
            raise NotFoundException(f"Segment {segment_order} not found")

        if target.content_script:
            return SessionDetailResponse.model_validate(session)

        # Get previous segment summary for continuity
        prev_summary = None
        if segment_order > 1:
            for seg in session.segments:
                if seg.segment_order == segment_order - 1 and seg.content_script:
                    prev_summary = seg.content_script[:500]
                    break

        material_summary = await self._get_material_summary(session)

        # Use session_evaluation to find segment info
        evaluation = session.session_evaluation or {}
        eval_segments = evaluation.get("segments", [])
        eval_seg = None
        for es in eval_segments:
            if es.get("segment_order") == segment_order:
                eval_seg = es
                break

        if eval_seg:
            content = await self._generate_segment_script(
                session, eval_seg, segment_order, prev_summary, material_summary
            )
        else:
            # Fallback to legacy prompt
            prompt = compose_segment_content_prompt(
                concept_name=session.concept_name,
                segment_title=target.title,
                segment_type=target.segment_type.value if hasattr(target.segment_type, "value") else target.segment_type,
                segment_order=segment_order,
                key_points=target.key_points,
                teaching_notes=target.teaching_notes,
                study_level=session.study_level.value,
                personality=session.model_personality.value,
                mood=session.mood.value,
                previous_segment_summary=prev_summary,
                user_material_summary=material_summary,
            )
            try:
                result = await generate_json_response(
                    system_prompt="You are an expert tutor generating a segment teaching script. Return valid JSON.",
                    user_message=prompt,
                    model=session.ai_model_used or "gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=4096,
                )
                content = result.get("content_script", "")
                if result.get("animation_cues"):
                    target.animation_cues = result["animation_cues"]
                if result.get("whiteboard_cues"):
                    target.whiteboard_cues = result["whiteboard_cues"]
            except Exception:
                logger.exception("Failed to generate content for segment %d", segment_order)
                content = (
                    f"Let's continue with {target.title}. "
                    f"We'll cover: {', '.join(target.key_points or ['the key concepts'])}."
                )

        target.content_script = content
        await self._db.flush()
        refreshed = await self._get_session_or_404(session_id, user_id)
        return SessionDetailResponse.model_validate(refreshed)

    # ── Pause / Complete / Cancel ──────────────────────────────────────

    async def pause_session(self, session_id: UUID, user_id: UUID) -> SessionResponse:
        session = await self._get_session_or_404(session_id, user_id)
        if session.status == SessionStatus.PAUSED:
            # Already paused — idempotent, return current state
            return SessionResponse.model_validate(session)
        if session.status != SessionStatus.IN_PROGRESS:
            raise BadRequestException("Session is not in progress")
        session.status = SessionStatus.PAUSED
        await self._db.flush()
        return SessionResponse.model_validate(session)

    async def complete_session(self, session_id: UUID, user_id: UUID) -> SessionResponse:
        session = await self._get_session_or_404(session_id, user_id)
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.completion_percentage = 100.0
        await self._db.flush()
        return SessionResponse.model_validate(session)

    async def cancel_session(self, session_id: UUID, user_id: UUID) -> SessionResponse:
        session = await self._get_session_or_404(session_id, user_id)
        session.status = SessionStatus.CANCELLED
        await self._db.flush()
        return SessionResponse.model_validate(session)

    # ── Get / List ─────────────────────────────────────────────────────

    async def get_session(self, session_id: UUID, user_id: UUID) -> SessionDetailResponse:
        session = await self._get_session_or_404(session_id, user_id)
        return SessionDetailResponse.model_validate(session)

    async def list_sessions(
        self, user_id: UUID, page: int = 1, page_size: int = 20
    ) -> SessionListResponse:
        count_q = select(func.count()).select_from(TutorSession).where(
            TutorSession.user_id == user_id
        )
        total = (await self._db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        q = (
            select(TutorSession, Subject.name.label("subject_name"))
            .outerjoin(Subject, TutorSession.subject_id == Subject.id)
            .where(TutorSession.user_id == user_id)
            .order_by(TutorSession.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self._db.execute(q)).all()
        sessions = []
        for session_row, subject_name in rows:
            data = SessionResponse.model_validate(session_row)
            data.subject_name = subject_name
            sessions.append(data)
        return SessionListResponse(
            sessions=sessions,
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Mid-session Config Update ──────────────────────────────────────

    async def update_session_config(
        self, session_id: UUID, user_id: UUID, data: SessionUpdate
    ) -> SessionResponse:
        session = await self._get_session_or_404(session_id, user_id)
        if session.status not in (SessionStatus.IN_PROGRESS, SessionStatus.PAUSED, SessionStatus.READY, SessionStatus.DRAFT):
            raise BadRequestException("Cannot update config for this session state")

        update_fields = data.model_dump(exclude_unset=True)
        if "mood" in update_fields:
            session.mood = update_fields["mood"]
        if "model_personality" in update_fields:
            session.model_personality = update_fields["model_personality"]
        if "language" in update_fields:
            session.language = update_fields["language"]
        if "study_level" in update_fields:
            session.study_level = update_fields["study_level"]
        if "voice_id" in update_fields:
            session.voice_id = update_fields["voice_id"]

        if session.config:
            for key, value in update_fields.items():
                if key == "extra":
                    session.config.extra = value
                elif hasattr(session.config, key):
                    setattr(session.config, key, value.value if hasattr(value, "value") else str(value))

        session.system_prompt_snapshot = self._recompose_system_prompt(session)

        # Invalidate pre-generated content for pending segments so they
        # regenerate with the new config on next SSE request.
        for seg in session.segments:
            if seg.status == SegmentStatus.PENDING and seg.content_script:
                seg.content_script = None
                logger.info(
                    "Invalidated prefetched content for segment %d (config change)",
                    seg.segment_order,
                )

        await self._db.flush()
        return SessionResponse.model_validate(session)

    # ── Playlist ───────────────────────────────────────────────────────

    async def get_playlist(self, playlist_id: UUID, user_id: UUID) -> PlaylistResponse:
        result = await self._db.execute(
            select(SessionPlaylist).where(
                SessionPlaylist.id == playlist_id,
                SessionPlaylist.user_id == user_id,
            )
        )
        playlist = result.scalar_one_or_none()
        if not playlist:
            raise NotFoundException("Playlist not found")
        return PlaylistResponse.model_validate(playlist)

    async def list_playlists(self, user_id: UUID, page: int = 1, page_size: int = 20) -> dict:
        """List all playlists for the current user with pagination."""
        count_q = select(func.count()).select_from(SessionPlaylist).where(
            SessionPlaylist.user_id == user_id
        )
        total = (await self._db.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        q = (
            select(SessionPlaylist)
            .where(SessionPlaylist.user_id == user_id)
            .order_by(SessionPlaylist.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self._db.execute(q)).scalars().all()
        playlists = []
        for p in rows:
            completed = sum(1 for s in (p.sessions or []) if s.status.value == "completed")
            playlists.append({
                "id": str(p.id),
                "title": p.title,
                "total_sessions": p.total_sessions,
                "completed_sessions": completed,
                "is_complete": p.is_complete,
                "created_at": p.created_at.isoformat(),
            })
        return {
            "playlists": playlists,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Check Auto-End Condition ───────────────────────────────────────

    async def should_auto_end(self, session_id: UUID, user_id: UUID) -> bool:
        """Check if all segments are completed or duration is exceeded."""
        session = await self._get_session_or_404(session_id, user_id)
        if session.status != SessionStatus.IN_PROGRESS:
            return False

        # Check if all segments completed
        if session.segments:
            all_done = all(
                seg.status == SegmentStatus.COMPLETED for seg in session.segments
            )
            if all_done:
                return True

        # Check if duration exceeded
        if session.started_at and session.total_duration_seconds:
            elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
            if elapsed >= session.total_duration_seconds:
                return True

        return False

    # ── Internal Helpers ───────────────────────────────────────────────

    def _get_previous_segment_summary(
        self, session: TutorSession, segment_order: int
    ) -> Optional[str]:
        """Return a truncated summary of the previous segment's content for AI context.

        Handles both the new structured JSON format and the legacy text script format.
        """
        if segment_order <= 1:
            return None
        for seg in session.segments:
            if seg.segment_order == segment_order - 1 and seg.content_script:
                script = seg.content_script
                # NEW FORMAT: extract text elements from JSON blocks
                try:
                    data = json.loads(script)
                    if isinstance(data, dict) and "blocks" in data:
                        texts: list[str] = []
                        for block in data.get("blocks", []):
                            for section in block.get("sections", []):
                                for el in section.get("elements", []):
                                    if el.get("type") == "text":
                                        texts.append(el.get("content", ""))
                                    elif el.get("type") == "list":
                                        texts.extend(el.get("items", []))
                        summary = " ".join(texts)
                        return summary[:_PREV_CONTEXT_CHARS]
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
                # LEGACY FORMAT: plain text script
                return script[:_PREV_CONTEXT_CHARS]
        return None

    def _find_eval_segment(
        self, session: TutorSession, segment_order: int
    ) -> Optional[dict]:
        """Look up the evaluation JSON entry for a segment order."""
        for es in (session.session_evaluation or {}).get("segments", []):
            if es.get("segment_order") == segment_order:
                return es
        return None

    async def _wait_for_content_script(
        self, session_id: UUID, segment_order: int, timeout: float = 15.0
    ) -> Optional[str]:
        """Poll the DB for content_script that a background prefetch task may be writing.

        Uses an independent ``AsyncSession`` so it can see commits from the
        background task (which uses its own session).
        """
        from app.database import AsyncSessionLocal
        import time

        deadline = time.monotonic() + timeout
        interval = 0.5

        while time.monotonic() < deadline:
            await asyncio.sleep(interval)
            async with AsyncSessionLocal() as fresh_db:
                result = await fresh_db.execute(
                    select(SessionSegment.content_script).where(
                        SessionSegment.session_id == session_id,
                        SessionSegment.segment_order == segment_order,
                    )
                )
                content = result.scalar_one_or_none()
                if content:
                    return content
            interval = min(interval * 1.5, 2.0)

        return None

    async def _get_session_or_404(self, session_id: UUID, user_id: UUID) -> TutorSession:
        result = await self._db.execute(
            select(TutorSession)
            .options(
                selectinload(TutorSession.segments),
                selectinload(TutorSession.config),
                selectinload(TutorSession.materials),
                selectinload(TutorSession.user),
            )
            .where(
                TutorSession.id == session_id,
                TutorSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException("Session not found")
        return session

    async def _get_material_summary(self, session: TutorSession) -> Optional[str]:
        """Get material summary from session materials."""
        if session.materials:
            summaries = [
                m.extracted_content[:500]
                for m in session.materials
                if m.extracted_content and not m.extracted_content.startswith("[")
            ]
            if summaries:
                return "\n---\n".join(summaries)
        return None

    async def _generate_segment_script(
        self,
        session: TutorSession,
        eval_segment: dict,
        segment_order: int,
        previous_summary: Optional[str],
        material_summary: Optional[str],
    ) -> str:
        """Generate structured JSON teaching content for a segment.

        Uses the new block-based structured format.  The full JSON is returned
        as a serialised string so it can be stored in ``content_script`` and
        later parsed by :func:`parse_script_to_sse_events`.
        """
        duration_seconds = eval_segment.get("duration_seconds", 300)
        wpm = calculate_target_wpm(
            session.model_personality.value, session.mood.value
        )
        target_word_count = round(wpm * duration_seconds / 60)

        # Resolve tutor name (best-effort; fallback to Arjun)
        tutor_name = "Arjun"
        if session.config and getattr(session.config, "voice_id", None):
            try:
                from uuid import UUID as _UUID
                vp_q = await self._db.execute(
                    select(VoiceProfile).where(
                        VoiceProfile.id == _UUID(session.config.voice_id)
                    )
                )
                vp = vp_q.scalar_one_or_none()
                if vp:
                    tutor_name = vp.tutor_name
            except Exception:
                pass

        # Build the structured-JSON–specific system prompt
        structured_system_prompt = compose_structured_teaching_system_prompt(
            tutor_name=tutor_name,
            language=session.language,
            user_type=(
                session.user.user_type.value
                if session.user
                else "self_learner"
            ),
            age=session.user.age if session.user else None,
            concept_name=session.concept_name,
            study_level=session.study_level.value,
            personality=session.model_personality.value,
            mood=session.mood.value,
            user_material_summary=material_summary,
        )

        # Build the user message (segment-specific teaching instruction)
        teaching_prompt = compose_session_teaching_prompt(
            session_evaluation=session.session_evaluation or {},
            segment_order=segment_order,
            system_prompt=structured_system_prompt,
            previous_segment_summary=previous_summary,
            user_material_summary=material_summary,
            target_word_count=target_word_count,
        )

        title = eval_segment.get("title", f"Segment {segment_order}")
        points = eval_segment.get("key_points", ["the key concepts"])

        try:
            result = await generate_json_response(
                system_prompt=structured_system_prompt,
                user_message=teaching_prompt,
                model=session.ai_model_used or "gpt-4o-mini",
                temperature=0.7,
                max_tokens=8192,
            )

            if isinstance(result, dict):
                # NEW FORMAT: structured JSON with blocks
                if "blocks" in result:
                    # Ensure topic is set
                    if not result.get("topic"):
                        result["topic"] = title
                    return json.dumps(result, ensure_ascii=False)

                # LEGACY FALLBACK: model returned old-style content_script
                if "content_script" in result:
                    return result["content_script"]

            return str(result) if result else ""

        except Exception:
            logger.exception("Failed to generate segment %d script", segment_order)
            # Minimal fallback — not ideal but keeps the session alive
            return json.dumps({
                "topic": title,
                "difficulty": "intermediate",
                "blocks": [
                    {
                        "id": "b1",
                        "title": title,
                        "estimated_time": duration_seconds,
                        "sections": [
                            {
                                "heading": "Overview",
                                "importance": "high",
                                "elements": [
                                    {
                                        "type": "text",
                                        "content": (
                                            f"Welcome to this segment on {title}. "
                                            f"We are going to explore {', '.join(points[:3])}. "
                                            "Let us dive in together and build a strong understanding step by step."
                                        ),
                                    },
                                    {
                                        "type": "list",
                                        "items": points[:5] if points else [f"Key concepts of {title}"],
                                    },
                                ],
                            }
                        ],
                        "next": [],
                        "references": [],
                    }
                ],
            }, ensure_ascii=False)

    async def _generate_goodbye(self, session: TutorSession) -> str:
        """Generate a humanly goodbye message from the AI tutor."""
        tutor_name = "Arjun"
        if session.voice_id:
            vp_result = await self._db.execute(
                select(VoiceProfile).where(VoiceProfile.id == session.voice_id)
            )
            voice = vp_result.scalar_one_or_none()
            if voice:
                tutor_name = voice.tutor_name

        completed = sum(1 for s in session.segments if s.status == SegmentStatus.COMPLETED)
        total = len(session.segments)

        prompt = compose_session_goodbye_prompt(
            tutor_name=tutor_name,
            concept_name=session.concept_name,
            personality=session.model_personality.value,
            language=session.language,
            segments_completed=completed,
            total_segments=total,
        )

        try:
            goodbye = await chat_completion(
                system_prompt=session.system_prompt_snapshot or "",
                user_message=prompt,
                model=session.ai_model_used or "gpt-4o-mini",
                temperature=0.8,
                max_tokens=300,
            )
            return goodbye
        except Exception:
            logger.exception("Failed to generate goodbye")
            return (
                f"[warm] Great job today! <pause:400ms> "
                f"We covered a lot about {session.concept_name}. "
                f"[encouraging] Keep practicing what we learned, and you'll master it in no time. "
                f"<pause:700ms> See you next time!"
            )

    def _recompose_system_prompt(self, session: TutorSession) -> str:
        """Recompose the system prompt from current session state."""
        tutor_name = "Arjun"
        user = session.user
        return compose_system_prompt(
            tutor_name=tutor_name,
            language=session.language,
            user_type=user.user_type.value if user else "self_learner",
            age=user.age if user else None,
            grade=user.grade if user else None,
            institution=user.institution if user else None,
            board=user.board if user else None,
            concept_name=session.concept_name,
            description=session.description,
            study_level=session.study_level.value,
            entire_session_type=session.entire_session_type.value,
            mood=session.mood.value,
            personality=session.model_personality.value,
            duration_type=session.duration_type.value,
            duration_minutes=session.duration_minutes,
            session_mode=session.session_mode.value,
        )

    def _estimate_duration(
        self, session_type: EntireSessionType, study_level: StudyLevel
    ) -> int:
        base_times = {
            EntireSessionType.BASIC_OVERVIEW: 30,
            EntireSessionType.REVISION: 30,
            EntireSessionType.INTERMEDIATE: 60,
            EntireSessionType.EXAM_FOCUSED: 60,
            EntireSessionType.IN_DEPTH: 120,
        }
        level_multipliers = {
            StudyLevel.BEGINNER: 1.2,
            StudyLevel.BASIC: 1.0,
            StudyLevel.INTERMEDIATE: 1.0,
            StudyLevel.ADVANCED: 1.3,
            StudyLevel.EXPERT: 1.5,
        }
        base = base_times.get(session_type, 60)
        mult = level_multipliers.get(study_level, 1.0)
        return min(int(base * mult), settings.MAX_SESSION_DURATION_MINUTES)

    def _fallback_evaluation(self, concept: str, duration_min: int) -> dict:
        """Provide a basic session_evaluation if AI generation fails."""
        total_seconds = duration_min * 60
        return {
            "session_overview": {
                "main_concept": concept,
                "description": f"A comprehensive session on {concept}",
                "target_audience": "General learner",
                "estimated_total_duration_seconds": total_seconds,
                "difficulty_rating": 3,
                "prerequisites": [],
            },
            "segments": [
                {
                    "segment_order": 1,
                    "segment_type": "introduction",
                    "title": f"Introduction to {concept}",
                    "description": f"Overview and introduction of {concept}",
                    "key_points": [f"Overview of {concept}"],
                    "duration_seconds": min(300, total_seconds // 6),
                    "teaching_approach": "Start with a warm greeting and broad overview",
                    "visual_aids": [],
                },
                {
                    "segment_order": 2,
                    "segment_type": "core_teaching",
                    "title": f"Core Concepts of {concept}",
                    "description": f"Deep dive into the main concepts of {concept}",
                    "key_points": [f"Key concepts of {concept}"],
                    "duration_seconds": total_seconds // 2,
                    "teaching_approach": "Explain concepts with examples and analogies",
                    "visual_aids": [],
                },
                {
                    "segment_order": 3,
                    "segment_type": "example",
                    "title": "Examples and Applications",
                    "description": "Real-world examples and practical applications",
                    "key_points": ["Practical applications"],
                    "duration_seconds": total_seconds // 4,
                    "teaching_approach": "Use relatable examples",
                    "visual_aids": [],
                },
                {
                    "segment_order": 4,
                    "segment_type": "summary",
                    "title": "Summary and Key Takeaways",
                    "description": "Recap of all concepts covered",
                    "key_points": ["Session summary"],
                    "duration_seconds": min(300, total_seconds // 6),
                    "teaching_approach": "Summarize and reinforce key takeaways",
                    "visual_aids": [],
                },
            ],
            "teaching_strategy": {
                "personality_approach": "Friendly and encouraging",
                "mood_adaptation": "Match the student's energy level",
                "engagement_techniques": ["Ask questions", "Use analogies", "Celebrate progress"],
                "language_style": "Clear and conversational",
            },
        }
