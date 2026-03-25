from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.interactions import router as interactions_router
from app.api.v1.content import router as content_router
from app.api.v1.curriculum import router as curriculum_router
from app.api.v1.voices import router as voices_router
from app.api.v1.materials import router as materials_router
from app.api.v1.speech import router as speech_router
from app.api.v1.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(interactions_router, prefix="/interactions", tags=["Interactions"])
api_router.include_router(content_router, prefix="/content", tags=["Content"])
api_router.include_router(curriculum_router, prefix="/curriculum", tags=["Curriculum"])
api_router.include_router(voices_router, prefix="/voices", tags=["Voices"])
api_router.include_router(materials_router, prefix="/materials", tags=["Materials"])
api_router.include_router(speech_router, prefix="/speech", tags=["Speech"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
