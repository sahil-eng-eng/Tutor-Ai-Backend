"""
Speech processing API — exposes text-to-speech-script conversion
and enriched TTS synthesis for the frontend audio player.
"""

from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.response import success_response
from app.services.speech_processor import enrich_for_speech, compute_voice_params
from app.services.ai_tutor_service import chat_completion

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


# ── Hinglish conversion ───────────────────────────────────────────────

HINGLISH_SYSTEM_PROMPT = """You are a Hinglish translator for an AI tutor platform.

Your job: Rewrite the given English text into natural, conversational Hinglish.

Rules:
1. Output ONLY Roman script (Latin alphabet). NEVER use Devanagari.
2. Mix Hindi words/phrases naturally into English sentence structure.
3. Keep technical terms, proper nouns, and numbers in English.
4. The output must be naturally speakable by a TTS engine.
5. Maintain the same meaning, tone, and educational intent.
6. Keep it conversational — like a friendly Indian tutor explaining.
7. Do NOT add extra content, greetings, or commentary.
8. Return ONLY the converted text, nothing else.

Examples:
- "Let's understand this concept step by step." → "Chaliye is concept ko step by step samajhte hain."
- "This is very important for your exam." → "Ye aapke exam ke liye bahut important hai."
- "Can you see how this formula works?" → "Kya aap dekh sakte hain ye formula kaise kaam karta hai?"
"""


class HinglishRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=50)


@router.post("/to-hinglish")
async def convert_to_hinglish(
    body: HinglishRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Convert a batch of English text strings to Hinglish (Roman script).
    Returns a list of converted strings in the same order.
    """
    if not body.texts:
        return success_response(data={"texts": []}, message="No texts to convert")

    joined = "\n---\n".join(body.texts)
    user_msg = f"Convert each text segment below to Hinglish. Separate outputs with ---\n\n{joined}"

    try:
        raw = await chat_completion(
            system_prompt=HINGLISH_SYSTEM_PROMPT,
            user_message=user_msg,
            temperature=0.6,
            max_tokens=len(joined) * 3,
        )
        parts = [p.strip() for p in raw.split("---")]
        # Ensure we have the right number of outputs
        if len(parts) < len(body.texts):
            parts.extend(body.texts[len(parts):])
        elif len(parts) > len(body.texts):
            parts = parts[:len(body.texts)]
        return success_response(data={"texts": parts}, message="Converted to Hinglish")
    except Exception:
        # Fallback: return original texts on error
        return success_response(data={"texts": body.texts}, message="Hinglish conversion failed, returning originals")
