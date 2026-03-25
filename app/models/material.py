import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SAEnum, Uuid, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from app.database import Base


class MaterialType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    QUESTION_BANK = "question_bank"


class UserMaterial(Base):
    __tablename__ = "user_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tutor_sessions.id", ondelete="SET NULL"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[MaterialType] = mapped_column(
        SAEnum(MaterialType, name="material_type_enum"), nullable=False
    )
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bytes
    extracted_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="materials")
    session = relationship("TutorSession", back_populates="materials")
