import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, Boolean, Enum as SAEnum, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from app.database import Base


class InteractionType(str, enum.Enum):
    DOUBT = "doubt"
    PULSE_CHECK = "pulse_check"
    MCQ = "mcq"
    CHAT = "chat"
    HAND_RAISE = "hand_raise"
    SEGMENT_TRANSITION = "segment_transition"
    CONFIG_CHANGE = "config_change"
    CELEBRATION = "celebration"
    CURIOSITY_TRIGGER = "curiosity_trigger"
    STORY = "story"


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        SAEnum(InteractionType, name="interaction_type_enum"), nullable=False
    )
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp_in_session_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="interactions")


class PulseMetric(Base):
    __tablename__ = "pulse_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "mcq_response", "verbal_response", "engagement_check", "response_time"
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp_in_session_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="pulse_metrics")


class DoubtRecord(Base):
    __tablename__ = "doubt_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("session_segments.id", ondelete="SET NULL"), nullable=True
    )
    doubt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    doubt_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "spoken", "typed", "go_ahead_button"
    timestamp_in_session_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="doubts")


class MCQQuestion(Base):
    __tablename__ = "mcq_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("session_segments.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    user_answer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
