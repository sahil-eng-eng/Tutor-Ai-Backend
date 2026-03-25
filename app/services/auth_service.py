from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.core.security import hash_password, verify_password
from app.config import settings
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    AuthTokens,
    ChangePassword,
    ForgotPassword,
    ResetPassword,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.otp import generate_otp


class AuthService:
    """Handles registration, login, verification, and token management."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def register(self, data: UserRegister) -> AuthResponse:
        existing = await self._db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictException("Email already registered")

        otp = generate_otp()
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            user_type=data.user_type,
            age=data.age,
            grade=data.grade,
            board=data.board,
            institution=data.institution,
            preferred_language=data.preferred_language,
            verification_code=otp,
            verification_code_expires=datetime.now(timezone.utc) + timedelta(
                minutes=settings.OTP_EXPIRY_MINUTES
            ),
        )
        self._db.add(user)
        await self._db.flush()

        # Send verification (no-op if service disabled)
        await send_verification_email(user.email, otp)

        tokens = self._issue_tokens(user)
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens,
        )

    async def login(self, email: str, password: str) -> AuthResponse:
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        tokens = self._issue_tokens(user)
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens,
        )

    async def verify_account(self, token: str) -> dict:
        """Verify account using OTP token sent to email."""
        result = await self._db.execute(
            select(User).where(User.verification_code == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise BadRequestException("Invalid verification token")
        if user.is_verified:
            raise BadRequestException("Account already verified")
        if (
            user.verification_code_expires
            and user.verification_code_expires < datetime.now(timezone.utc)
        ):
            raise BadRequestException("Verification token expired")

        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires = None
        await self._db.flush()
        return {"message": "Email verified successfully"}

    async def resend_verification(self, email: str) -> dict:
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        if user.is_verified:
            raise BadRequestException("Account already verified")

        otp = generate_otp()
        user.verification_code = otp
        user.verification_code_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        await self._db.flush()
        await send_verification_email(user.email, otp)
        return {"message": "Verification code sent"}

    async def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise UnauthorizedException("Invalid or expired refresh token")
        user_id = payload.get("sub")
        result = await self._db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedException("User not found")
        return self._issue_tokens(user)

    async def change_password(
        self, user: User, data: ChangePassword
    ) -> dict:
        if not verify_password(data.current_password, user.password_hash):
            raise BadRequestException("Current password is incorrect")
        user.password_hash = hash_password(data.new_password)
        await self._db.flush()
        return {"message": "Password changed successfully"}

    async def forgot_password(self, email: str) -> dict:
        """Generate a password reset token and (placeholder) send via email."""
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        # Always return success for security reasons (don't leak email existence)
        if not user or not user.is_active:
            return {"message": "Password reset instructions sent to your email"}

        reset_token = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        user.reset_password_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        await self._db.flush()
        await send_password_reset_email(user.email, reset_token)
        return {"message": "Password reset instructions sent to your email"}

    async def reset_password(self, token: str, new_password: str) -> dict:
        """Reset password using the token from email."""
        result = await self._db.execute(
            select(User).where(User.reset_password_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise BadRequestException("Token expired or invalid")
        if (
            user.reset_password_expires
            and user.reset_password_expires < datetime.now(timezone.utc)
        ):
            raise BadRequestException("Token expired or invalid")

        user.password_hash = hash_password(new_password)
        user.reset_password_token = None
        user.reset_password_expires = None
        await self._db.flush()
        return {"message": "Password reset successfully"}

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _issue_tokens(user: User) -> AuthTokens:
        token_data = {"sub": str(user.id), "email": user.email}
        return AuthTokens(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
