from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.curriculum import VoiceProfileResponse
from app.schemas.response import success_response
from app.services.voice_service import VoiceService

router = APIRouter()


@router.get("")
async def list_voices(db: AsyncSession = Depends(get_db)):
    service = VoiceService(db)
    result = await service.list_voices()
    return success_response(data=result, message="Voices retrieved")


@router.get("/{voice_id}")
async def get_voice(voice_id: UUID, db: AsyncSession = Depends(get_db)):
    service = VoiceService(db)
    result = await service.get_voice(voice_id)
    return success_response(data=result, message="Voice profile retrieved")
