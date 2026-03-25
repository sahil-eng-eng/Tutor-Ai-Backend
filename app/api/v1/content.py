from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.session import TutorSession
from app.core.exceptions import NotFoundException
from app.schemas.content import SessionContentResponse, SessionNotesResponse
from app.schemas.response import success_response
from app.services.content_generation_service import ContentGenerationService
from app.services.whiteboard_engine import generate_whiteboard_timeline
from app.utils.pdf_generator import generate_notes_pdf

router = APIRouter()


@router.post("/{session_id}/generate")
async def generate_content(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContentGenerationService(db)
    result = await service.generate_session_content(session_id, user.id)
    return success_response(data=result, message="Content generated")


@router.get("/{session_id}")
async def get_content(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContentGenerationService(db)
    result = await service.get_session_content(session_id, user.id)
    return success_response(data=result, message="Content retrieved")


@router.get("/{session_id}/whiteboard-timeline")
async def get_whiteboard_timeline(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the synchronized whiteboard instruction timeline for a session.

    Returns timed whiteboard events (text, formulas, diagrams, code)
    matched to segment positions for frontend canvas rendering.
    """
    result = await db.execute(
        select(TutorSession).where(
            TutorSession.id == session_id,
            TutorSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Session not found")

    segments_data = [
        {
            "segment_order": seg.segment_order,
            "title": seg.title,
            "content_script": seg.content_script or "",
            "duration_seconds": seg.duration_seconds or 0,
            "whiteboard_cues": seg.whiteboard_cues,
            "animation_cues": seg.animation_cues,
        }
        for seg in sorted(session.segments, key=lambda s: s.segment_order)
    ]

    timeline = generate_whiteboard_timeline(segments_data)
    return success_response(data=timeline, message="Whiteboard timeline generated")


@router.post("/{session_id}/notes")
async def generate_notes(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContentGenerationService(db)
    result = await service.generate_notes(session_id, user.id)
    return success_response(data=result, message="Notes generated")


@router.get("/{session_id}/notes/pdf")
async def download_notes_pdf(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContentGenerationService(db)
    content = await service.get_session_content(session_id, user.id)
    if not content.notes:
        notes = await service.generate_notes(session_id, user.id)
    else:
        notes = content.notes

    pdf_bytes = generate_notes_pdf(
        title=f"Session Notes",
        content_markdown=notes.content_markdown or "",
        key_points=notes.key_points,
        formulas=notes.formulas,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=session_notes_{session_id}.pdf"},
    )
