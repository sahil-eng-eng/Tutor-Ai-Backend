import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class UserType(str, enum.Enum):
    SCHOOL_STUDENT = "school_student"
    COLLEGE_STUDENT = "college_student"
    WORKING_PROFESSIONAL = "working_professional"
    SELF_LEARNER = "self_learner"
    COMPETITIVE_EXAM = "competitive_exam"


class UserProfession(str, enum.Enum):
    """Profession selected at session creation time (not a user profile field)."""
    STUDENT = "student"
    COLLEGE_STUDENT = "college_student"
    WORKING_PROFESSIONAL = "working_professional"
    COMPETITIVE_EXAMS = "competitive_exams"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[UserType] = mapped_column(
        SAEnum(UserType, name="user_type_enum"), nullable=False
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    board: Mapped[str | None] = mapped_column(String(100), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(50), default="english")
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    verification_code_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Password reset
    reset_password_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reset_password_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 2FA / TOTP
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    sessions = relationship("TutorSession", back_populates="user", lazy="selectin")
    materials = relationship("UserMaterial", back_populates="user", lazy="selectin")
