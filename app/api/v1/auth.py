from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.response import success_response
from app.schemas.user import (
    AuthResponse,
    AuthTokens,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyAccount,
    ResendVerification,
    ForgotPassword,
    ResetPassword,
    RefreshTokenRequest,
    ChangePassword,
)
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.models.user import User
from app.core.jwt_handler import decode_token
from app.core.token_blacklist import blacklist_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_scheme = HTTPBearer()

router = APIRouter()


@router.post("/register", status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.register(data)
    return success_response(data=result, message="Registration successful")


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.login(data.email, data.password)
    return success_response(data=result, message="Login successful")


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    """Invalidate the current access token by blacklisting its JTI."""
    payload = decode_token(credentials.credentials)
    if payload and payload.get("jti"):
        import time
        exp = payload.get("exp", 0)
        ttl = max(int(exp - time.time()), 0)
        if ttl > 0:
            await blacklist_token(payload["jti"], ttl)
    return success_response(data=None, message="Logged out successfully")


@router.post("/verify")
async def verify_account(data: VerifyAccount, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.verify_account(data.token)
    return success_response(data=result, message="Email verified successfully")


@router.post("/resend-verification")
async def resend_verification(data: ResendVerification, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.resend_verification(data.email)
    return success_response(data=result, message="Verification code resent to your email")


@router.post("/forgot-password")
async def forgot_password(data: ForgotPassword, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.forgot_password(data.email)
    return success_response(data=result, message="Password reset instructions sent to your email")


@router.post("/reset-password")
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.reset_password(data.token, data.new_password)
    return success_response(data=result, message="Password reset successfully")


@router.post("/refresh")
async def refresh_tokens(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.refresh_tokens(data.refresh_token)
    return success_response(data=result, message="Tokens refreshed")


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.change_password(user, data)
    return success_response(data=result, message="Password changed successfully")
