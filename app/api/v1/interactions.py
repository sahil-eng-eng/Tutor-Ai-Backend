from typing import Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_handler import verify_access_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.interaction import (
    ChatMessageRequest,
    DoubtResponse,
    DoubtResolveRequest,
    HandRaiseRequest,
    InteractionResponse,
    LiveDoubtRequest,
    MCQResponse,
    MCQSubmitRequest,
    PulseAdjustRequest,
    PulseCheckResponse,
    PulseRecordRequest,
)
from app.schemas.response import success_response
from app.services.doubt_service import DoubtService
from app.services.pulse_service import PulseService
from app.utils.file_handler import save_upload, validate_file_extension

router = APIRouter()


async def _get_user_from_token_or_header(request: Request, db: AsyncSession) -> User:
    """Auth via Authorization header OR ?token= query param (for SSE POST endpoints)."""
    from fastapi import HTTPException, status as http_status
    from sqlalchemy import select

    token: Optional[str] = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    from uuid import UUID as _UUID
    result = await db.execute(select(User).where(User.id == _UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


# ── Doubt / Hand Raise ─────────────────────────────────────────────────

@router.post("/hand-raise")
async def hand_raise(
    data: HandRaiseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DoubtService(db)
    result = await service.hand_raise(
        data.session_id, user.id, data.timestamp_in_session_seconds
    )
    # Auto-track pulse activity
    pulse_svc = PulseService(db)
    await pulse_svc.record_activity(
        data.session_id, user.id, "hand_raise",
        timestamp_seconds=data.timestamp_in_session_seconds,
    )
    return success_response(data=result, message="Hand raised acknowledged")


@router.post("/doubts")
async def submit_doubt_text(
    session_id: UUID = Form(...),
    doubt_text: Optional[str] = Form(None),
    timestamp_in_session_seconds: Optional[int] = Form(None),
    doubt_image: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image_path = None
    if doubt_image and doubt_image.filename:
        if not validate_file_extension(doubt_image.filename, "image"):
            from app.core.exceptions import BadRequestException
            raise BadRequestException("Invalid image format")
        content = await doubt_image.read()
        image_path = await save_upload(content, doubt_image.filename, "doubts")

    service = DoubtService(db)
    result = await service.submit_doubt(
        session_id=session_id,
        user_id=user.id,
        doubt_text=doubt_text,
        doubt_image_path=image_path,
        timestamp_seconds=timestamp_in_session_seconds,
    )
    # Auto-track pulse activity (raising a doubt = engaged)
    pulse_svc = PulseService(db)
    await pulse_svc.record_activity(
        session_id, user.id, "doubt_raised",
        timestamp_seconds=timestamp_in_session_seconds,
    )
    return success_response(data=result, message="Doubt submitted")


@router.post("/doubts/resolve")
async def resolve_doubt(
    data: DoubtResolveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DoubtService(db)
    result = await service.resolve_doubt(
        doubt_id=data.doubt_id,
        session_id=data.doubt_id,
        user_id=user.id,
        resolution_method=data.resolution_method,
        user_message=data.user_message,
    )
    return success_response(data=result, message="Doubt resolved")


@router.get("/doubts/{session_id}")
async def list_session_doubts(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DoubtService(db)
    result = await service.list_doubts(session_id, user.id)
    return success_response(data=result, message="Doubts retrieved")


# ── Pulse / MCQ ────────────────────────────────────────────────────────

@router.get("/pulse/{session_id}")
async def get_pulse(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PulseService(db)
    result = await service.get_current_pulse(session_id, user.id)
    return success_response(data=result, message="Pulse retrieved")


@router.post("/pulse/{session_id}/record")
async def record_pulse(
    session_id: UUID,
    data: PulseRecordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PulseService(db)
    result = await service.record_pulse(
        session_id, user.id,
        metric_type="focus",
        score=data.focus_level,
        max_score=100.0,
        details={"notes": data.notes} if data.notes else None,
        timestamp_seconds=data.timestamp_in_session_seconds,
    )
    return success_response(data=result, message="Pulse recorded")


@router.post("/pulse/{session_id}/adjust")
async def adjust_pulse(
    session_id: UUID,
    data: PulseAdjustRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Frontend-triggered real-time pulse adjustment.
    Send a positive delta to increase or negative delta to decrease the pulse meter."""
    service = PulseService(db)
    result = await service.adjust_pulse(
        session_id, user.id, data.adjustment, data.reason, data.timestamp_in_session_seconds
    )
    return success_response(data=result, message="Pulse adjusted")


@router.post("/pulse/{session_id}/activity")
async def record_activity(
    session_id: UUID,
    activity_type: str,
    timestamp_seconds: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a user activity event (doubt_raised, chat_message, hand_raise, etc.)
    and automatically adjust the pulse meter based on the activity type."""
    service = PulseService(db)
    result = await service.record_activity(
        session_id, user.id, activity_type,
        timestamp_seconds=timestamp_seconds,
    )
    return success_response(data=result, message="Activity recorded")


@router.post("/mcq/{session_id}/generate")
async def generate_mcq(
    session_id: UUID,
    topic: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PulseService(db)
    result = await service.generate_mcq_check(session_id, user.id, topic)
    return success_response(data=result, message="MCQs generated")


@router.post("/mcq/submit")
async def submit_mcq_answer(
    data: MCQSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PulseService(db)
    result = await service.submit_mcq_answer(
        data.session_id, user.id, data.question_id, data.user_answer
    )
    return success_response(data=result, message="MCQ answer submitted")


# ── Chat ───────────────────────────────────────────────────────────────

@router.post("/chat")
async def send_chat_message(
    data: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.interaction import Interaction, InteractionType
    from app.models.session import TutorSession
    from sqlalchemy import select
    from app.services.ai_tutor_service import chat_completion
    from app.core.exceptions import NotFoundException

    result = await db.execute(
        select(TutorSession).where(
            TutorSession.id == data.session_id,
            TutorSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session not found")

    try:
        ai_response = await chat_completion(
            system_prompt=session.system_prompt_snapshot or "",
            user_message=data.message,
            model=session.ai_model_used or "",
        )
    except Exception:
        ai_response = "I'm here to help! Could you rephrase your question?"

    interaction = Interaction(
        session_id=data.session_id,
        interaction_type=InteractionType.CHAT,
        user_message=data.message,
        ai_response=ai_response,
        timestamp_in_session_seconds=data.timestamp_in_session_seconds,
    )
    db.add(interaction)
    await db.flush()

    # Auto-track pulse activity
    pulse_svc = PulseService(db)
    await pulse_svc.record_activity(
        data.session_id, user.id, "chat_message",
        timestamp_seconds=data.timestamp_in_session_seconds,
    )

    result = InteractionResponse.model_validate(interaction)
    return success_response(data=result, message="Chat response generated")


# ── Live Doubt Streaming ───────────────────────────────────────────────

@router.post("/doubts/{session_id}/stream-answer")
async def stream_live_doubt_answer(
    session_id: UUID,
    data: LiveDoubtRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream an AI answer to a live doubt raised during segment playback.

    Emits Server-Sent Events: ``doubt_start`` → ``text`` (×N) → ``doubt_end``.
    Pulse is incremented by +4 on completion.

    Auth: ``Authorization: Bearer <token>`` header **or** ``?token=<jwt>`` query param.
    """
    user = await _get_user_from_token_or_header(request, db)
    doubt_svc = DoubtService(db)
    pulse_svc = PulseService(db)

    async def event_generator():
        try:
            async for event_str in doubt_svc.stream_live_doubt(
                session_id, user.id, data.query_text, data.segment_order
            ):
                yield event_str
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'code': 'server_error', 'message': str(exc)})}\n\n"
            return
        finally:
            try:
                await pulse_svc.record_activity(session_id, user.id, "live_doubt_resolved")
                await db.commit()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
