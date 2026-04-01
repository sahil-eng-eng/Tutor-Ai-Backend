import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────────

class UserMood(str, enum.Enum):
    VERY_FOCUSED = "very_focused"
    FOCUSED = "focused"
    LIGHT = "light"
    NON_ATTENTIVE = "non_attentive"
    TIRED = "tired"
    CURIOUS = "curious"
    EXAM_PREP = "exam_prep"


class ModelPersonality(str, enum.Enum):
    STRICT = "strict"
    VERY_FRIENDLY = "very_friendly"
    ATTENTIVE = "attentive"
    FUNNY = "funny"
    MOTIVATIONAL = "motivational"
    PATIENT = "patient"
    STORYTELLER = "storyteller"


class DurationType(str, enum.Enum):
    USER_DEFINED = "user_defined"
    AI_DETERMINED = "ai_determined"


class SessionMode(str, enum.Enum):
    SINGLE_SESSION = "single_session"        # single session with multiple segments
    MULTIPLE_SESSIONS = "multiple_sessions"  # playlist of sessions


class StudyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class EntireSessionType(str, enum.Enum):
    BASIC_OVERVIEW = "basic_overview"
    INTERMEDIATE = "intermediate"
    IN_DEPTH = "in_depth"
    EXAM_FOCUSED = "exam_focused"
    REVISION = "revision"


class SessionStatus(str, enum.Enum):
    DRAFT = "draft"
    PREPARING = "preparing"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SegmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SegmentType(str, enum.Enum):
    INTRODUCTION = "introduction"
    CORE_TEACHING = "core_teaching"
    EXAMPLE = "example"
    ANALOGY = "analogy"
    WHITEBOARD = "whiteboard"
    ANIMATION_DEMO = "animation_demo"
    PRACTICE = "practice"
    QA_CHECK = "qa_check"
    STORY = "story"
    CURIOSITY_TRIGGER = "curiosity_trigger"
    RECAP = "recap"
    SUMMARY = "summary"


# ── Models ─────────────────────────────────────────────────────────────

class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    playlist_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("session_playlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    playlist_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Core fields
    concept_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[UserMood] = mapped_column(
        SAEnum(UserMood, name="user_mood_enum"), nullable=False
    )
    model_personality: Mapped[ModelPersonality] = mapped_column(
        SAEnum(ModelPersonality, name="model_personality_enum"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(50), default="english")
    duration_type: Mapped[DurationType] = mapped_column(
        SAEnum(DurationType, name="duration_type_enum"), nullable=False
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("voice_profiles.id"), nullable=True
    )
    session_mode: Mapped[SessionMode] = mapped_column(
        SAEnum(SessionMode, name="session_mode_enum"), nullable=False
    )
    study_level: Mapped[StudyLevel] = mapped_column(
        SAEnum(StudyLevel, name="study_level_enum"), nullable=False
    )
    entire_session_type: Mapped[EntireSessionType] = mapped_column(
        SAEnum(EntireSessionType, name="entire_session_type_enum"), nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status_enum"), default=SessionStatus.DRAFT
    )

    # Curriculum link (optional)
    board_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("curriculum_boards.id"), nullable=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("curriculum_subjects.id"), nullable=True
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("curriculum_chapters.id"), nullable=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("curriculum_topics.id"), nullable=True
    )

    # College-student flow fields
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    course: Mapped[str | None] = mapped_column(String(255), nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Working-professional flow field
    professional_background: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # User profession for this session
    user_profession: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # AI model info
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    system_prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-generated session evaluation JSON
    session_evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Computed metadata
    total_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    pulse_percentage: Mapped[float] = mapped_column(Float, default=50.0)
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="sessions")
    playlist = relationship("SessionPlaylist", back_populates="sessions")
    segments = relationship(
        "SessionSegment", back_populates="session", order_by="SessionSegment.segment_order",
        lazy="selectin",
    )
    interactions = relationship("Interaction", back_populates="session", lazy="selectin")
    pulse_metrics = relationship("PulseMetric", back_populates="session", lazy="selectin")
    doubts = relationship("DoubtRecord", back_populates="session", lazy="selectin")
    notes = relationship("SessionNotes", back_populates="session", uselist=False, lazy="selectin")
    config = relationship("SessionConfig", back_populates="session", uselist=False, lazy="selectin")
    animations = relationship("AnimationData", back_populates="session", lazy="selectin")
    whiteboards = relationship("WhiteboardData", back_populates="session", lazy="selectin")
    materials = relationship("UserMaterial", back_populates="session", lazy="selectin")


class SessionSegment(Base):
    __tablename__ = "session_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False
    )
    segment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_type: Mapped[SegmentType] = mapped_column(
        SAEnum(SegmentType, name="segment_type_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    teaching_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[SegmentStatus] = mapped_column(
        SAEnum(SegmentStatus, name="segment_status_enum"), default=SegmentStatus.PENDING
    )
    animation_cues: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    whiteboard_cues: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    visuals_ready: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TutorSession", back_populates="segments")


class SessionConfig(Base):
    """Mutable configuration snapshot that can be changed mid-session."""

    __tablename__ = "session_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tutor_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    personality: Mapped[str] = mapped_column(String(50), nullable=False)
    study_level: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    session = relationship("TutorSession", back_populates="config")


class SessionPlaylist(Base):
    __tablename__ = "session_playlists"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    concept_name: Mapped[str] = mapped_column(String(500), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sessions = relationship("TutorSession", back_populates="playlist", lazy="selectin")
