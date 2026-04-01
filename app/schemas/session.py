from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.session import (
    UserMood,
    ModelPersonality,
    DurationType,
    SessionMode,
    StudyLevel,
    EntireSessionType,
    SessionStatus,
    SegmentStatus,
    SegmentType,
)
from app.models.user import UserProfession


# ── Session Create ─────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """
    Unified session creation payload.

    Required fields vary by user_profession:
    - student: board_id, class_name, subject_id, chapter_id required
    - college_student: university, course, semester, subject_id, chapter_id required
    - working_professional: professional_background required
    - competitive_exams: (no extra required fields)
    """
    # User profession (drives the flow)
    user_profession: UserProfession

    concept_name: str = Field(..., min_length=2, max_length=500)
    description: Optional[str] = None
    mood: UserMood
    model_personality: ModelPersonality
    language: str = "english"
    duration_type: DurationType
    duration_minutes: Optional[int] = Field(None, ge=10, le=180)
    voice_id: Optional[UUID] = None
    session_mode: SessionMode
    study_level: StudyLevel
    entire_session_type: EntireSessionType

    # Student (school) flow fields
    board_id: Optional[UUID] = None
    class_name: Optional[str] = None        # e.g. "10th", "12th"
    subject_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None

    # College student flow fields
    university: Optional[str] = None        # free text or external API
    course: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)

    # Working professional flow field
    professional_background: Optional[str] = None

    # Optional user material IDs
    material_ids: Optional[list[UUID]] = None

    @model_validator(mode="after")
    def validate_profession_fields(self):
        p = self.user_profession
        if p == UserProfession.STUDENT:
            if not self.board_id:
                raise ValueError("board_id is required for student profession")
            if not self.class_name:
                raise ValueError("class_name is required for student profession")
        elif p == UserProfession.COLLEGE_STUDENT:
            if not self.university:
                raise ValueError("university is required for college_student profession")
            if not self.course:
                raise ValueError("course is required for college_student profession")
            if self.semester is None:
                raise ValueError("semester is required for college_student profession")
        elif p == UserProfession.WORKING_PROFESSIONAL:
            if not self.professional_background:
                raise ValueError("professional_background is required for working_professional profession")
        return self


class SessionUpdate(BaseModel):
    mood: Optional[UserMood] = None
    model_personality: Optional[ModelPersonality] = None
    language: Optional[str] = None
    study_level: Optional[StudyLevel] = None
    voice_id: Optional[UUID] = None
    extra: Optional[dict[str, Any]] = None


class SessionEvaluationUpdate(BaseModel):
    """Frontend sends updated session_evaluation JSON after preview editing."""
    session_evaluation: dict[str, Any]


# ── Segment ────────────────────────────────────────────────────────────

class SegmentResponse(BaseModel):
    id: UUID
    session_id: UUID
    segment_order: int
    segment_type: SegmentType
    title: str
    content_script: Optional[str] = None
    teaching_notes: Optional[str] = None
    duration_seconds: Optional[int] = None
    status: SegmentStatus
    animation_cues: Optional[dict] = None
    whiteboard_cues: Optional[dict] = None
    key_points: Optional[list] = None
    visuals_ready: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Session Response ───────────────────────────────────────────────────

class SessionConfigResponse(BaseModel):
    id: UUID
    session_id: UUID
    mood: str
    personality: str
    study_level: str
    language: str
    voice_id: Optional[str] = None
    extra: Optional[dict] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    playlist_id: Optional[UUID] = None
    playlist_order: Optional[int] = None
    user_profession: Optional[str] = None
    concept_name: str
    description: Optional[str] = None
    subject_name: Optional[str] = None  # resolved from subject_id for frontend filtering
    mood: UserMood
    model_personality: ModelPersonality
    language: str
    duration_type: DurationType
    duration_minutes: Optional[int] = None
    voice_id: Optional[UUID] = None
    session_mode: SessionMode
    study_level: StudyLevel
    entire_session_type: EntireSessionType
    status: SessionStatus
    ai_model_used: Optional[str] = None
    total_duration_seconds: Optional[int] = None
    pulse_average: Optional[float] = None
    pulse_percentage: Optional[float] = None
    completion_percentage: float
    board_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    chapter_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    university: Optional[str] = None
    course: Optional[str] = None
    semester: Optional[int] = None
    professional_background: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    segments: list[SegmentResponse] = []
    config: Optional[SessionConfigResponse] = None
    session_evaluation: Optional[dict] = None


class SessionPreviewResponse(BaseModel):
    """Returned by the preview API — exposes session_evaluation for display."""
    session_id: UUID
    concept_name: str
    description: Optional[str] = None
    user_profession: Optional[str] = None
    status: SessionStatus
    session_evaluation: Optional[dict] = None
    total_duration_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
    page: int
    page_size: int


# ── Playlist ───────────────────────────────────────────────────────────

class PlaylistResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    concept_name: str
    total_sessions: int
    is_complete: bool
    created_at: datetime
    sessions: list[SessionResponse] = []

    model_config = {"from_attributes": True}
