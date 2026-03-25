import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from app.database import Base


class AnimationType(str, enum.Enum):
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    NETWORK_GRAPH = "network_graph"
    TIMELINE = "timeline"
    PROCESS_ANIMATION = "process_animation"
    COMPARISON = "comparison"
    HIERARCHY = "hierarchy"
    REAL_WORLD_ANALOGY = "real_world_analogy"
    CODE_WALKTHROUGH = "code_walkthrough"
    MATH_VISUALIZATION = "math_visualization"
    CUSTOM = "custom"


class AnimationData(Base):
    __tablename__ = "animation_data"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("session_segments.id", ondelete="SET NULL"), nullable=True
    )
    animation_type: Mapped[AnimationType] = mapped_column(
        SAEnum(AnimationType, name="animation_type_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    animation_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    trigger_timestamp_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="animations")


class WhiteboardData(Base):
    __tablename__ = "whiteboard_data"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("session_segments.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)  # formula, diagram, text, code
    whiteboard_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    trigger_timestamp_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="whiteboards")


class SessionNotes(Base):
    __tablename__ = "session_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tutor_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    formulas: Mapped[list | None] = mapped_column(JSON, nullable=True)
    diagrams: Mapped[list | None] = mapped_column(JSON, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="notes")
