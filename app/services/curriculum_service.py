"""
Curriculum Service — manages boards, subjects, chapters, topics, question banks.
Supports both school (Board → Standard/Class → Subject → Chapter → Topic) and
college (University → Course/Degree → Semester → Subject → Chapter → Topic) paths.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.curriculum import Board, Subject, Chapter, Topic, QuestionBank
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


class CurriculumService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Boards ──────────────────────────────────────────────────────────

    async def list_boards(
        self, board_type: Optional[str] = None
    ) -> list[BoardResponse]:
        q = select(Board)
        if board_type:
            q = q.where(Board.board_type == board_type)
        q = q.order_by(Board.name)
        result = await self._db.execute(q)
        return [BoardResponse.model_validate(b) for b in result.scalars().all()]

    async def get_board(self, board_id: UUID) -> BoardDetailResponse:
        result = await self._db.execute(select(Board).where(Board.id == board_id))
        board = result.scalar_one_or_none()
        if not board:
            raise NotFoundException("Board not found")
        return BoardDetailResponse.model_validate(board)

    async def create_board(self, data: BoardCreate) -> BoardResponse:
        board = Board(
            name=data.name,
            description=data.description,
            country=data.country,
            board_type=data.board_type,
        )
        self._db.add(board)
        await self._db.flush()
        return BoardResponse.model_validate(board)

    # ── Subjects ────────────────────────────────────────────────────────

    async def list_subjects(
        self,
        board_id: UUID,
        grade: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> list[SubjectResponse]:
        q = select(Subject).where(Subject.board_id == board_id)
        if grade:
            q = q.where(Subject.grade == grade)
        if semester:
            q = q.where(Subject.semester == semester)
        q = q.order_by(Subject.name)
        result = await self._db.execute(q)
        return [SubjectResponse.model_validate(s) for s in result.scalars().all()]

    async def get_subject(self, subject_id: UUID) -> SubjectDetailResponse:
        result = await self._db.execute(select(Subject).where(Subject.id == subject_id))
        subject = result.scalar_one_or_none()
        if not subject:
            raise NotFoundException("Subject not found")
        return SubjectDetailResponse.model_validate(subject)

    async def create_subject(self, data: SubjectCreate) -> SubjectResponse:
        subject = Subject(
            board_id=data.board_id,
            name=data.name,
            grade=data.grade,
            semester=data.semester,
            description=data.description,
        )
        self._db.add(subject)
        await self._db.flush()
        return SubjectResponse.model_validate(subject)

    # ── Chapters ────────────────────────────────────────────────────────

    async def list_chapters(self, subject_id: UUID) -> list[ChapterResponse]:
        result = await self._db.execute(
            select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.chapter_number)
        )
        return [ChapterResponse.model_validate(c) for c in result.scalars().all()]

    async def get_chapter(self, chapter_id: UUID) -> ChapterDetailResponse:
        result = await self._db.execute(select(Chapter).where(Chapter.id == chapter_id))
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise NotFoundException("Chapter not found")
        return ChapterDetailResponse.model_validate(chapter)

    async def create_chapter(self, data: ChapterCreate) -> ChapterResponse:
        chapter = Chapter(
            subject_id=data.subject_id,
            name=data.name,
            chapter_number=data.chapter_number,
            description=data.description,
            estimated_hours=data.estimated_hours,
        )
        self._db.add(chapter)
        await self._db.flush()
        return ChapterResponse.model_validate(chapter)

    # ── Topics ──────────────────────────────────────────────────────────

    async def list_topics(self, chapter_id: UUID) -> list[TopicResponse]:
        result = await self._db.execute(
            select(Topic).where(Topic.chapter_id == chapter_id).order_by(Topic.topic_number)
        )
        return [TopicResponse.model_validate(t) for t in result.scalars().all()]

    async def get_topic(self, topic_id: UUID) -> TopicResponse:
        result = await self._db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundException("Topic not found")
        return TopicResponse.model_validate(topic)

    async def create_topic(self, data: TopicCreate) -> TopicResponse:
        topic = Topic(
            chapter_id=data.chapter_id,
            name=data.name,
            topic_number=data.topic_number,
            description=data.description,
            key_concepts=data.key_concepts,
            estimated_minutes=data.estimated_minutes,
        )
        self._db.add(topic)
        await self._db.flush()
        return TopicResponse.model_validate(topic)

    # ── Question Banks ──────────────────────────────────────────────────

    async def create_question_bank(
        self, user_id: UUID, data: QuestionBankCreate
    ) -> QuestionBankResponse:
        qb = QuestionBank(
            user_id=user_id,
            topic_id=data.topic_id,
            title=data.title,
            questions=data.questions,
            is_predefined=False,
        )
        self._db.add(qb)
        await self._db.flush()
        return QuestionBankResponse.model_validate(qb)

    async def list_question_banks(
        self, topic_id: Optional[UUID] = None, user_id: Optional[UUID] = None
    ) -> list[QuestionBankResponse]:
        q = select(QuestionBank)
        if topic_id:
            q = q.where(QuestionBank.topic_id == topic_id)
        if user_id:
            q = q.where(
                (QuestionBank.user_id == user_id) | (QuestionBank.is_predefined == True)
            )
        result = await self._db.execute(q)
        return [QuestionBankResponse.model_validate(qb) for qb in result.scalars().all()]
