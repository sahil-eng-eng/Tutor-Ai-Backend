from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.session import TutorSession
from app.schemas.user import UserResponse, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_user(self, user_id: UUID) -> UserResponse:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        return UserResponse.model_validate(user)

    async def update_user(self, user: User, data: UserUpdate) -> UserResponse:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        await self._db.flush()
        return UserResponse.model_validate(user)

    async def deactivate_user(self, user: User) -> dict:
        user.is_active = False
        await self._db.flush()
        return {"message": "Account deactivated"}

    async def get_stats(self, user_id: UUID) -> dict:
        """Compute dashboard stats for the user."""
        from app.models.session import SessionStatus

        # Fetch all completed sessions (only fields we need)
        q = select(
            TutorSession.total_duration_seconds,
            TutorSession.completion_percentage,
            TutorSession.concept_name,
            TutorSession.completed_at,
        ).where(
            TutorSession.user_id == user_id,
            TutorSession.status == SessionStatus.COMPLETED,
        )
        rows = (await self._db.execute(q)).all()

        hours_studied = sum(
            (r.total_duration_seconds or 0) for r in rows
        ) / 3600.0

        # topics_mastered: distinct concept_names with completion >= 80%
        mastered = {
            r.concept_name
            for r in rows
            if (r.completion_percentage or 0) >= 80.0
        }
        topics_mastered = len(mastered)

        # avg_score
        scores = [r.completion_percentage for r in rows if r.completion_percentage is not None]
        avg_score = (sum(scores) / len(scores)) if scores else 0.0

        # day_streak: consecutive days (UTC) up to today with ≥1 completed session
        completed_days = {
            r.completed_at.astimezone(timezone.utc).date()
            for r in rows
            if r.completed_at is not None
        }
        today = datetime.now(timezone.utc).date()
        streak = 0
        check = today
        while check in completed_days:
            streak += 1
            check -= timedelta(days=1)

        # weekly_hours: Mon–Sun of current UTC week (7 elements)
        monday = today - timedelta(days=today.weekday())
        week_seconds: list[float] = [0.0] * 7
        for r in rows:
            if r.completed_at is None:
                continue
            day = r.completed_at.astimezone(timezone.utc).date()
            if monday <= day < monday + timedelta(days=7):
                idx = day.weekday()
                week_seconds[idx] += r.total_duration_seconds or 0
        weekly_hours = [round(s / 3600.0, 2) for s in week_seconds]

        return {
            "hours_studied": round(hours_studied, 2),
            "day_streak": streak,
            "topics_mastered": topics_mastered,
            "avg_score": round(avg_score, 2),
            "weekly_hours": weekly_hours,
        }
