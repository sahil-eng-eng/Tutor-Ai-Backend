from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.content import AnimationType


class AnimationResponse(BaseModel):
    id: UUID
    session_id: UUID
    segment_id: Optional[UUID] = None
    animation_type: AnimationType
    title: str
    description: Optional[str] = None
    animation_spec: dict
    trigger_timestamp_seconds: Optional[int] = None
    duration_seconds: Optional[int] = None
    sync_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WhiteboardResponse(BaseModel):
    id: UUID
    session_id: UUID
    segment_id: Optional[UUID] = None
    title: str
    content_type: str
    whiteboard_spec: dict
    trigger_timestamp_seconds: Optional[int] = None
    sync_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionNotesResponse(BaseModel):
    id: UUID
    session_id: UUID
    content_markdown: Optional[str] = None
    key_points: Optional[list] = None
    formulas: Optional[list] = None
    diagrams: Optional[list] = None
    transcript: Optional[str] = None
    pdf_path: Optional[str] = None
    generated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentTimelineItem(BaseModel):
    timestamp_seconds: int
    content_type: str  # "animation", "whiteboard", "speech"
    data: dict[str, Any]


class SessionContentResponse(BaseModel):
    session_id: UUID
    animations: list[AnimationResponse] = []
    whiteboards: list[WhiteboardResponse] = []
    notes: Optional[SessionNotesResponse] = None
