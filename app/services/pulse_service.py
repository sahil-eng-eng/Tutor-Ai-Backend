"""
Pulse Service — Activity-based engagement tracking for live sessions.

The pulse meter is a 0–100 percentage that reflects the student's engagement.
It starts at 50% and is adjusted up or down by:
- Backend events: doubts raised, chat messages, MCQ responses, hand raises
- Frontend triggers: the frontend can call the adjust API with a delta
- Inactivity decay: long periods without interaction lower the pulse

Higher pulse = more engaged student.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, BadRequestException
from app.models.interaction import PulseMetric, MCQQuestion, Interaction, InteractionType
from app.models.session import TutorSession, SessionStatus
from app.prompts.interaction_prompts import (
    PULSE_LOW_RESPONSES,
    PULSE_CHECK_QUESTIONS,
    get_random_response,
)
from app.prompts.prompt_composer import compose_mcq_generation_prompt
from app.schemas.interaction import PulseCheckResponse, MCQResponse
from app.services.ai_tutor_service import generate_json_response
from app.services.model_selector_service import get_model_for_mcq_generation

logger = logging.getLogger("ai_tutor")

# Pulse adjustment deltas for automatic backend events
PULSE_DELTAS = {
    "doubt_raised": +8,
    "chat_message": +5,
    "hand_raise": +10,
    "mcq_correct": +12,
    "mcq_incorrect": -3,
    "go_ahead": +3,
    "config_change": +2,
    "inactivity": -10,
    "live_doubt_resolved": +4,
}


class PulseService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Record an activity event (backend-triggered) ───────────────────

    async def record_activity(
        self,
        session_id: UUID,
        user_id: UUID,
        activity_type: str,
        details: Optional[dict] = None,
        timestamp_seconds: Optional[int] = None,
    ) -> PulseCheckResponse:
        """Record a user activity event and adjust the pulse meter accordingly.

        activity_type can be: doubt_raised, chat_message, hand_raise,
        mcq_correct, mcq_incorrect, go_ahead, config_change, inactivity
        """
        session = await self._get_session(session_id, user_id)

        delta = PULSE_DELTAS.get(activity_type, 0)
        new_pulse = max(0.0, min(100.0, session.pulse_percentage + delta))
        session.pulse_percentage = new_pulse

        # Store metric record
        metric = PulseMetric(
            session_id=session_id,
            metric_type=activity_type,
            score=new_pulse,
            max_score=100.0,
            details=details or {"delta": delta, "activity": activity_type},
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(metric)
        await self._db.flush()

        return await self._compute_pulse_status(session)

    # ── Adjust pulse from frontend (explicit increase/decrease) ────────

    async def adjust_pulse(
        self,
        session_id: UUID,
        user_id: UUID,
        delta: float,
        reason: Optional[str] = None,
        timestamp_seconds: Optional[int] = None,
    ) -> PulseCheckResponse:
        """Frontend-triggered real-time pulse adjustment.

        delta: positive to increase, negative to decrease (clamped to -50..+50)
        """
        session = await self._get_session(session_id, user_id)
        if session.status != SessionStatus.IN_PROGRESS:
            raise BadRequestException("Can only adjust pulse for in-progress sessions")

        # Clamp delta to prevent extreme jumps
        delta = max(-50.0, min(50.0, delta))
        new_pulse = max(0.0, min(100.0, session.pulse_percentage + delta))
        session.pulse_percentage = new_pulse

        metric = PulseMetric(
            session_id=session_id,
            metric_type="frontend_adjust",
            score=new_pulse,
            max_score=100.0,
            details={"delta": delta, "reason": reason or "frontend_triggered"},
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(metric)
        await self._db.flush()

        return await self._compute_pulse_status(session)

    # ── Legacy record pulse (backward compatibility) ───────────────────

    async def record_pulse(
        self,
        session_id: UUID,
        user_id: UUID,
        metric_type: str,
        score: float,
        max_score: float = 100.0,
        details: Optional[dict] = None,
        timestamp_seconds: Optional[int] = None,
    ) -> PulseCheckResponse:
        session = await self._get_session(session_id, user_id)

        metric = PulseMetric(
            session_id=session_id,
            metric_type=metric_type,
            score=score,
            max_score=max_score,
            details=details,
            timestamp_in_session_seconds=timestamp_seconds,
        )
        self._db.add(metric)
        await self._db.flush()

        return await self._compute_pulse_status(session)

    # ── Get current pulse ──────────────────────────────────────────────

    async def get_current_pulse(
        self, session_id: UUID, user_id: UUID
    ) -> PulseCheckResponse:
        session = await self._get_session(session_id, user_id)
        return await self._compute_pulse_status(session)

    # ── MCQ Generation ─────────────────────────────────────────────────

    async def generate_mcq_check(
        self, session_id: UUID, user_id: UUID, topic: str
    ) -> list[MCQResponse]:
        session = await self._get_session(session_id, user_id)

        prompt = compose_mcq_generation_prompt(
            topic=topic,
            study_level=session.study_level.value,
            count=3,
        )

        try:
            result = await generate_json_response(
                system_prompt="You are a quiz question generator. Return valid JSON array.",
                user_message=prompt,
                model=get_model_for_mcq_generation(),
                temperature=0.6,
            )
            questions_data = result if isinstance(result, list) else result.get("questions", [])
        except Exception:
            logger.exception("Failed to generate MCQs")
            questions_data = [
                {
                    "question": f"What is the key concept behind {topic}?",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "correct_answer": "A) Option 1",
                    "explanation": "This is the correct answer.",
                }
            ]

        mcqs = []
        for q_data in questions_data:
            mcq = MCQQuestion(
                session_id=session_id,
                question=q_data.get("question", ""),
                options=q_data.get("options", []),
                correct_answer=q_data.get("correct_answer", ""),
                explanation=q_data.get("explanation"),
            )
            self._db.add(mcq)
            mcqs.append(mcq)

        interaction = Interaction(
            session_id=session_id,
            interaction_type=InteractionType.PULSE_CHECK,
            ai_response=get_random_response(PULSE_CHECK_QUESTIONS),
            metadata_json={"mcq_count": len(mcqs), "topic": topic},
        )
        self._db.add(interaction)
        await self._db.flush()

        return [MCQResponse.model_validate(m) for m in mcqs]

    async def submit_mcq_answer(
        self,
        session_id: UUID,
        user_id: UUID,
        question_id: UUID,
        user_answer: str,
    ) -> MCQResponse:
        session = await self._get_session(session_id, user_id)

        result = await self._db.execute(
            select(MCQQuestion).where(
                MCQQuestion.id == question_id,
                MCQQuestion.session_id == session_id,
            )
        )
        mcq = result.scalar_one_or_none()
        if not mcq:
            raise NotFoundException("Question not found")

        mcq.user_answer = user_answer
        mcq.is_correct = user_answer.strip().lower() == mcq.correct_answer.strip().lower()

        # Record pulse from MCQ
        activity_type = "mcq_correct" if mcq.is_correct else "mcq_incorrect"
        delta = PULSE_DELTAS[activity_type]
        session.pulse_percentage = max(0.0, min(100.0, session.pulse_percentage + delta))

        metric = PulseMetric(
            session_id=session_id,
            metric_type=activity_type,
            score=session.pulse_percentage,
            details={"question_id": str(question_id), "is_correct": mcq.is_correct, "delta": delta},
        )
        self._db.add(metric)
        await self._db.flush()

        return MCQResponse.model_validate(mcq)

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

    async def _compute_pulse_status(self, session: TutorSession) -> PulseCheckResponse:
        """Compute current pulse status from session's pulse_percentage and recent metrics."""
        result = await self._db.execute(
            select(PulseMetric)
            .where(PulseMetric.session_id == session.id)
            .order_by(PulseMetric.created_at.desc())
            .limit(10)
        )
        metrics = result.scalars().all()

        current_pulse = session.pulse_percentage
        if metrics:
            scores = [m.score for m in metrics]
            average_pulse = sum(scores) / len(scores)
        else:
            average_pulse = current_pulse

        session.pulse_average = average_pulse
        await self._db.flush()

        recommendation = None
        should_downgrade = False
        should_change_personality = False

        if current_pulse < settings.PULSE_LOW_THRESHOLD:
            recommendation = get_random_response(PULSE_LOW_RESPONSES)
            should_downgrade = True
            should_change_personality = True

        return PulseCheckResponse(
            session_id=session.id,
            current_pulse=current_pulse,
            average_pulse=average_pulse,
            pulse_percentage=current_pulse,
            recommendation=recommendation,
            should_downgrade_level=should_downgrade,
            should_change_personality=should_change_personality,
            details={
                "total_checks": len(metrics),
                "recent_activities": [
                    {"type": m.metric_type, "score": m.score}
                    for m in metrics[:5]
                ],
            },
        )
