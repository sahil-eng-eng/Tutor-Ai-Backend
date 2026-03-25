import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column


from app.database import Base


class SessionCache(Base):
    """Cache prebuilt sessions so identical concept requests can reuse content."""

    __tablename__ = "session_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    concept_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    concept_name: Mapped[str] = mapped_column(String(500), nullable=False)
    study_level: Mapped[str] = mapped_column(String(50), nullable=False)
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segments_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    animations_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    whiteboard_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    script_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
