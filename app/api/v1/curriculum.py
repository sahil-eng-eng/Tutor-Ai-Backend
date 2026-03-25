from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.curriculum import (
    BoardResponse,
    BoardDetailResponse,
    BoardCreate,
    SubjectResponse,
    SubjectDetailResponse,
    SubjectCreate,
    ChapterResponse,
    ChapterDetailResponse,
    ChapterCreate,
    TopicResponse,
    TopicCreate,
    QuestionBankResponse,
    QuestionBankCreate,
)
from app.schemas.response import success_response
from app.services.curriculum_service import CurriculumService

router = APIRouter()


# ── Boards ──────────────────────────────────────────────────────────────

@router.get("/boards")
async def list_boards(
    board_type: Optional[str] = Query(None, description="Filter: school, university, competitive_exam"),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.list_boards(board_type)
    return success_response(data=result, message="Boards retrieved")


@router.get("/boards/{board_id}")
async def get_board(board_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.get_board(board_id)
    return success_response(data=result, message="Board retrieved")


@router.post("/boards", status_code=201)
async def create_board(
    data: BoardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.create_board(data)
    return success_response(data=result, message="Board created")


# ── Subjects ────────────────────────────────────────────────────────────

@router.get("/boards/{board_id}/subjects")
async def list_subjects(
    board_id: UUID,
    grade: Optional[str] = Query(None, description="Class/Standard for school, Course/Degree for college"),
    semester: Optional[str] = Query(None, description="Semester number (college only)"),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.list_subjects(board_id, grade, semester)
    return success_response(data=result, message="Subjects retrieved")


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.get_subject(subject_id)
    return success_response(data=result, message="Subject retrieved")


@router.post("/subjects", status_code=201)
async def create_subject(
    data: SubjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.create_subject(data)
    return success_response(data=result, message="Subject created")


# ── Chapters ────────────────────────────────────────────────────────────

@router.get("/subjects/{subject_id}/chapters")
async def list_chapters(subject_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.list_chapters(subject_id)
    return success_response(data=result, message="Chapters retrieved")


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.get_chapter(chapter_id)
    return success_response(data=result, message="Chapter retrieved")


@router.post("/chapters", status_code=201)
async def create_chapter(
    data: ChapterCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.create_chapter(data)
    return success_response(data=result, message="Chapter created")


# ── Topics ──────────────────────────────────────────────────────────────

@router.get("/chapters/{chapter_id}/topics")
async def list_topics(chapter_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.list_topics(chapter_id)
    return success_response(data=result, message="Topics retrieved")


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    service = CurriculumService(db)
    result = await service.get_topic(topic_id)
    return success_response(data=result, message="Topic retrieved")


@router.post("/topics", status_code=201)
async def create_topic(
    data: TopicCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.create_topic(data)
    return success_response(data=result, message="Topic created")


# ── Question Banks ──────────────────────────────────────────────────────

@router.post("/question-banks", status_code=201)
async def create_question_bank(
    data: QuestionBankCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.create_question_bank(user.id, data)
    return success_response(data=result, message="Question bank created")


@router.get("/question-banks")
async def list_question_banks(
    topic_id: Optional[UUID] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CurriculumService(db)
    result = await service.list_question_banks(topic_id, user.id)
    return success_response(data=result, message="Question banks retrieved")
