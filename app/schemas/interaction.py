from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.interaction import InteractionType


# ── Doubt ──────────────────────────────────────────────────────────────

class HandRaiseRequest(BaseModel):
    session_id: UUID
    timestamp_in_session_seconds: Optional[int] = None


class DoubtSubmitRequest(BaseModel):
    session_id: UUID
    doubt_text: Optional[str] = None
    # doubt_image handled via multipart upload
    timestamp_in_session_seconds: Optional[int] = None


class DoubtResolveRequest(BaseModel):
    doubt_id: UUID
    resolution_method: str = "go_ahead_button"
    user_message: Optional[str] = None


class LiveDoubtRequest(BaseModel):
    """Live doubt query during active segment streaming."""
    query_text: str = Field(..., min_length=3, max_length=2000)
    segment_order: Optional[int] = Field(None, ge=1)


class DoubtResponse(BaseModel):
    id: UUID
    session_id: UUID
    segment_id: Optional[UUID] = None
    doubt_text: Optional[str] = None
    ocr_extracted_text: Optional[str] = None
    ai_response: Optional[str] = None
    is_resolved: bool
    resolution_method: Optional[str] = None
    timestamp_in_session_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pulse ──────────────────────────────────────────────────────────────

class PulseCheckResponse(BaseModel):
    session_id: UUID
    current_pulse: float
    average_pulse: float
    pulse_percentage: Optional[float] = None
    recommendation: Optional[str] = None
    should_downgrade_level: bool = False
    should_change_personality: bool = False
    details: Optional[dict] = None


class PulseRecordRequest(BaseModel):
    """Self-reported focus level from the frontend."""
    focus_level: float = Field(..., ge=0, le=100, description="Focus level 0–100")
    notes: Optional[str] = Field(None, max_length=500)
    timestamp_in_session_seconds: Optional[int] = None


class PulseAdjustRequest(BaseModel):
    """Frontend-triggered pulse adjustment."""
    adjustment: float = Field(..., ge=-50, le=50, description="Amount to adjust pulse (-50 to +50)")
    reason: Optional[str] = Field(None, max_length=200)
    timestamp_in_session_seconds: Optional[int] = None


class MCQSubmitRequest(BaseModel):
    session_id: UUID
    question_id: UUID
    user_answer: str


class MCQResponse(BaseModel):
    id: UUID
    session_id: UUID
    question: str
    options: list
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    explanation: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Interaction ────────────────────────────────────────────────────────

class InteractionResponse(BaseModel):
    id: UUID
    session_id: UUID
    interaction_type: InteractionType
    user_message: Optional[str] = None
    ai_response: Optional[str] = None
    metadata_json: Optional[dict] = None
    timestamp_in_session_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageRequest(BaseModel):
    session_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)
    timestamp_in_session_seconds: Optional[int] = None
