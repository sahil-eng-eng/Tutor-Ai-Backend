from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class BoardResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    country: str
    board_type: str = "school"
    created_at: datetime

    model_config = {"from_attributes": True}


class SubjectResponse(BaseModel):
    id: UUID
    board_id: UUID
    name: str
    grade: str
    semester: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterResponse(BaseModel):
    id: UUID
    subject_id: UUID
    name: str
    chapter_number: int
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    id: UUID
    chapter_id: UUID
    name: str
    topic_number: int
    description: Optional[str] = None
    key_concepts: Optional[list] = None
    estimated_minutes: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubjectDetailResponse(SubjectResponse):
    chapters: list[ChapterResponse] = []


class ChapterDetailResponse(ChapterResponse):
    topics: list[TopicResponse] = []


class BoardDetailResponse(BoardResponse):
    subjects: list[SubjectResponse] = []


class QuestionBankResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    title: str
    questions: list
    is_predefined: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionBankCreate(BaseModel):
    topic_id: Optional[UUID] = None
    title: str
    questions: list[dict]


class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    country: str = "India"
    board_type: str = "school"  # school | university | competitive_exam


class SubjectCreate(BaseModel):
    board_id: UUID
    name: str
    grade: str
    semester: Optional[str] = None
    description: Optional[str] = None


class ChapterCreate(BaseModel):
    subject_id: UUID
    name: str
    chapter_number: int
    description: Optional[str] = None
    estimated_hours: Optional[int] = None


class TopicCreate(BaseModel):
    chapter_id: UUID
    name: str
    topic_number: int
    description: Optional[str] = None
    key_concepts: Optional[list] = None
    estimated_minutes: Optional[int] = None


class VoiceProfileResponse(BaseModel):
    id: UUID
    name: str
    language: str
    gender: str
    accent: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None
    tutor_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialUploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    file_name: str
    file_type: str
    file_size: Optional[int] = None  # bytes
    extracted_content: Optional[str] = None
    processed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
