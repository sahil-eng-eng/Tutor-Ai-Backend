from uuid import UUID
from typing import Optional
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.response import success_response
from app.schemas.session import (
    SessionCreate,
    SessionDetailResponse,
    SessionEvaluationUpdate,
    SessionListResponse,
    SessionPreviewResponse,
    SessionResponse,
    SessionUpdate,
    PlaylistResponse,
)
from app.services.session_service import SessionService
from app.core.jwt_handler import verify_access_token
from app.core.exceptions import NotFoundException, BadRequestException
from sqlalchemy import select

router = APIRouter()


async def _get_user_from_token_or_header(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via Authorization header or ?token= query param (for SSE/EventSource)."""
    from fastapi import HTTPException, status

    token: Optional[str] = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


@router.post("", status_code=201)
async def create_session(
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new session. AI evaluates all inputs and generates session_evaluation JSON."""
    service = SessionService(db)
    result = await service.create_session(user, data)
    return success_response(data=result, message="Session created")


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.list_sessions(user.id, page, page_size)
    return success_response(data=result, message="Sessions retrieved")


# Playlists registered BEFORE /{session_id} to avoid route shadowing

@router.get("/playlists")
async def list_playlists(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all playlists for the current user."""
    service = SessionService(db)
    result = await service.list_playlists(user.id, page, page_size)
    return success_response(data=result, message="Playlists retrieved")


@router.get("/playlists/{playlist_id}")
async def get_playlist(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.get_playlist(playlist_id, user.id)
    return success_response(data=result, message="Playlist retrieved")


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.get_session(session_id, user.id)
    return success_response(data=result, message="Session retrieved")


@router.get("/{session_id}/preview")
async def preview_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return session_evaluation data for frontend preview before starting."""
    service = SessionService(db)
    result = await service.preview_session(session_id, user.id)
    return success_response(data=result, message="Session preview retrieved")


@router.put("/{session_id}/evaluation")
async def update_session_evaluation(
    session_id: UUID,
    data: SessionEvaluationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update session_evaluation JSON after user edits topics in preview."""
    service = SessionService(db)
    result = await service.update_session_evaluation(session_id, user.id, data.session_evaluation)
    return success_response(data=result, message="Session evaluation updated")


@router.post("/{session_id}/start")
async def start_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start the session: builds segments from evaluation, generates first segment content."""
    service = SessionService(db)
    result = await service.start_session(session_id, user.id)
    return success_response(data=result, message="Session started")


@router.post("/{session_id}/pause")
async def pause_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.pause_session(session_id, user.id)
    return success_response(data=result, message="Session paused")


@router.post("/{session_id}/complete")
async def complete_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.complete_session(session_id, user.id)
    return success_response(data=result, message="Session completed")


@router.post("/{session_id}/cancel")
async def cancel_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    result = await service.cancel_session(session_id, user.id)
    return success_response(data=result, message="Session cancelled")


@router.post("/{session_id}/end")
async def end_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End session manually. AI tutor generates a humanly goodbye message."""
    service = SessionService(db)
    result = await service.end_session(session_id, user.id)
    return success_response(data=result, message="Session ended")


@router.post("/{session_id}/segments/{segment_order}/generate")
async def generate_segment_content(
    session_id: UUID,
    segment_order: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate content for a specific segment on demand (lazy generation)."""
    service = SessionService(db)
    result = await service.generate_next_segment_content(session_id, user.id, segment_order)
    return success_response(data=result, message=f"Segment {segment_order} content generated")


@router.get("/{session_id}/segments/{segment_order}/stream")
async def stream_segment_teaching(
    session_id: UUID,
    segment_order: int,
    request: Request,
    from_chunk: int = Query(0, ge=0, description="Resume stream from this chunk number (0 = start)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream segment teaching content as Server-Sent Events.

    - Waits for background prefetch if content is not yet ready.
    - Fires background generation of segment N+1 while streaming N.
    - Emits ``segment_end`` after every segment, ``session_end`` after the last.

    Auth: ``Authorization: Bearer <token>`` header **or** ``?token=<jwt>`` query param.
    """
    user = await _get_user_from_token_or_header(request, db)
    service = SessionService(db)

    async def event_generator():
        try:
            async for event_str in service.stream_segment_teaching(
                session_id, user.id, segment_order, from_chunk=from_chunk
            ):
                yield event_str

        except NotFoundException as exc:
            yield f"data: {json.dumps({'type': 'error', 'code': 'not_found', 'message': str(exc)})}\n\n"
        except BadRequestException as exc:
            yield f"data: {json.dumps({'type': 'error', 'code': 'bad_request', 'message': str(exc)})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'code': 'server_error', 'message': 'An unexpected error occurred'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{session_id}/config")
async def update_session_config(
    session_id: UUID,
    data: SessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SessionService(db)
    await service.update_session_config(session_id, user.id, data)
    applied = data.model_dump(exclude_unset=True, exclude_none=True)
    applied_serialized = {
        k: (v.value if hasattr(v, "value") else str(v))
        for k, v in applied.items()
        if k != "extra"
    }
    return success_response(
        data={"session_id": str(session_id), "applied": applied_serialized},
        message="Config updated",
    )
