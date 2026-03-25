from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserType


# ── Request Schemas ────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    user_type: UserType
    age: Optional[int] = Field(None, ge=5, le=100)
    grade: Optional[str] = None
    board: Optional[str] = None
    institution: Optional[str] = None
    preferred_language: str = "english"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    user_type: Optional[UserType] = None
    age: Optional[int] = Field(None, ge=5, le=100)
    grade: Optional[str] = None
    board: Optional[str] = None
    institution: Optional[str] = None
    preferred_language: Optional[str] = None
    bio: Optional[str] = None


class VerifyAccount(BaseModel):
    token: str = Field(..., min_length=4, max_length=10, description="OTP/verification token sent to email")


class ResendVerification(BaseModel):
    email: EmailStr


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Response Schemas ───────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    user_type: UserType
    age: Optional[int] = None
    grade: Optional[str] = None
    board: Optional[str] = None
    institution: Optional[str] = None
    preferred_language: str
    bio: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: AuthTokens
