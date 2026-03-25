import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON, Uuid, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.database import Base


class Board(Base):
    """Represents both school boards (CBSE, ICSE) and universities (IIT, VTU).

    - For schools: board_type='school', name='CBSE' / 'ICSE' etc.
    - For colleges: board_type='university', name='VTU' / 'Mumbai University' etc.
    """
    __tablename__ = "curriculum_boards"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India")
    board_type: Mapped[str] = mapped_column(
        String(50), default="school"
    )  # school | university | competitive_exam
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    subjects = relationship("Subject", back_populates="board", lazy="selectin")


class Subject(Base):
    """Subject within a board/university.

    - For schools: grade='10' (class/standard), semester=None
    - For colleges: grade='B.Tech CSE' (course/degree), semester='3' (semester number)
    """
    __tablename__ = "curriculum_subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    board_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("curriculum_boards.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)  # class/standard for school, course/degree for college
    semester: Mapped[str | None] = mapped_column(String(20), nullable=True)  # semester number for college
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    board = relationship("Board", back_populates="subjects")
    chapters = relationship("Chapter", back_populates="subject", lazy="selectin")


class Chapter(Base):
    __tablename__ = "curriculum_chapters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("curriculum_subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    subject = relationship("Subject", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", lazy="selectin")


class Topic(Base):
    __tablename__ = "curriculum_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("curriculum_chapters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    topic_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_concepts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chapter = relationship("Chapter", back_populates="topics")


class QuestionBank(Base):
    __tablename__ = "question_banks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("curriculum_topics.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    questions: Mapped[list] = mapped_column(JSON, nullable=False)
    is_predefined: Mapped[bool] = mapped_column(default=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
