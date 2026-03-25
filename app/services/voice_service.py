"""
Voice Service — integrates with ElevenLabs for TTS with dynamic voice parameters.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ServiceUnavailableException
from app.models.voice import VoiceProfile
from app.schemas.curriculum import VoiceProfileResponse
from app.services.speech_processor import (
    compute_voice_params,
    enrich_for_speech,
    Emotion,
    SegmentEnergy,
)

logger = logging.getLogger("ai_tutor")

_voice_client: Optional[httpx.AsyncClient] = None


def _get_voice_client() -> httpx.AsyncClient:
    global _voice_client
    if _voice_client is None or _voice_client.is_closed:
        _voice_client = httpx.AsyncClient(
            base_url=settings.ELEVENLABS_BASE_URL,
            headers={
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    return _voice_client


class VoiceService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_voices(self) -> list[VoiceProfileResponse]:
        result = await self._db.execute(select(VoiceProfile))
        voices = result.scalars().all()
        return [VoiceProfileResponse.model_validate(v) for v in voices]

    async def get_voice(self, voice_id: UUID) -> VoiceProfileResponse:
        result = await self._db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_id)
        )
        voice = result.scalar_one_or_none()
        if not voice:
            raise NotFoundException("Voice profile not found")
        return VoiceProfileResponse.model_validate(voice)

    async def synthesize_speech(
        self,
        text: str,
        voice_id: UUID,
        *,
        personality: str = "very_friendly",
        mood: str = "focused",
        segment_type: str = "core_teaching",
    ) -> bytes:
        """
        Convert text to speech via ElevenLabs with dynamic voice parameters.
        Parameters are computed from personality, mood, and segment context.
        Returns raw audio bytes (mp3).
        """
        voice_result = await self._db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_id)
        )
        voice = voice_result.scalar_one_or_none()
        if not voice:
            raise NotFoundException("Voice profile not found")

        if not settings.ELEVENLABS_API_KEY:
            raise ServiceUnavailableException("ElevenLabs API key not configured")

        voice_settings = compute_voice_params(
            personality=personality,
            mood=mood,
        )

        client = _get_voice_client()
        try:
            response = await client.post(
                f"/text-to-speech/{voice.elevenlabs_voice_id}",
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": voice_settings,
                },
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError:
            logger.exception("ElevenLabs TTS request failed")
            raise ServiceUnavailableException("Voice synthesis failed")

    async def synthesize_speech_enriched(
        self,
        text: str,
        voice_id: UUID,
        *,
        personality: str = "very_friendly",
        mood: str = "focused",
        segment_type: str = "core_teaching",
    ) -> list[dict]:
        """
        Process text through the speech processor and synthesize each chunk
        with its own voice parameters (emotion-aware, energy-aware).

        Returns list of {audio: bytes, pause_after_ms: int} dicts.
        """
        voice_result = await self._db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_id)
        )
        voice = voice_result.scalar_one_or_none()
        if not voice:
            raise NotFoundException("Voice profile not found")

        if not settings.ELEVENLABS_API_KEY:
            raise ServiceUnavailableException("ElevenLabs API key not configured")

        speech_data = enrich_for_speech(
            text,
            personality=personality,
            segment_type=segment_type,
            mood=mood,
        )

        client = _get_voice_client()
        audio_segments = []
        for segment in speech_data["tts_segments"]:
            try:
                response = await client.post(
                    f"/text-to-speech/{voice.elevenlabs_voice_id}",
                    json={
                        "text": segment["text"],
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": segment["voice_settings"],
                    },
                )
                response.raise_for_status()
                audio_segments.append({
                    "audio": response.content,
                    "pause_after_ms": segment["pause_after_ms"],
                })
            except httpx.HTTPStatusError:
                logger.warning("TTS chunk failed, skipping: %s", segment["text"][:50])
                continue

        return audio_segments

    async def synthesize_speech_stream(
        self,
        text: str,
        voice_id: UUID,
        *,
        personality: str = "very_friendly",
        mood: str = "focused",
    ):
        """Stream TTS audio chunks with dynamic voice parameters."""
        voice_result = await self._db.execute(
            select(VoiceProfile).where(VoiceProfile.id == voice_id)
        )
        voice = voice_result.scalar_one_or_none()
        if not voice:
            raise NotFoundException("Voice profile not found")

        if not settings.ELEVENLABS_API_KEY:
            raise ServiceUnavailableException("ElevenLabs API key not configured")

        voice_settings = compute_voice_params(
            personality=personality,
            mood=mood,
        )

        client = _get_voice_client()
        async with client.stream(
            "POST",
            f"/text-to-speech/{voice.elevenlabs_voice_id}/stream",
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": voice_settings,
            },
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                yield chunk
