"""
Speech processing API — exposes text-to-speech-script conversion
and enriched TTS synthesis for the frontend audio player.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.response import success_response
from app.services.speech_processor import enrich_for_speech, compute_voice_params

router = APIRouter()


class SpeechEnrichRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    personality: str = "very_friendly"
    mood: str = "focused"
    segment_type: str = "core_teaching"


class VoiceParamsRequest(BaseModel):
    personality: str = "very_friendly"
    mood: str = "focused"
    emotion: str = "neutral"
    segment_energy: str = "medium"


@router.post("/enrich")
async def enrich_text_for_speech(
    body: SpeechEnrichRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Process raw LLM text into speech-optimized segments with:
    - Emotion-aware voice parameters per chunk
    - Pause durations between chunks
    - Plain text fallback
    """
    result = enrich_for_speech(
        body.text,
        personality=body.personality,
        mood=body.mood,
        segment_type=body.segment_type,
    )
    return success_response(data=result, message="Text enriched for speech")


@router.post("/voice-params")
async def get_dynamic_voice_params(
    body: VoiceParamsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Compute ElevenLabs voice_settings for a given context.
    Useful for frontend to configure TTS calls directly.
    """
    params = compute_voice_params(
        personality=body.personality,
        mood=body.mood,
    )
    return success_response(data=params, message="Voice parameters computed")
