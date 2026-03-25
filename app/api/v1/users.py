from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.response import success_response
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService
from app.services.totp_service import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    generate_qr_code_base64,
    verify_totp_code,
)
from app.core.exceptions import BadRequestException

router = APIRouter()


@router.get("/me")
async def get_current_user_profile(user: User = Depends(get_current_user)):
    print(f"Current user: {user.email} (ID: {user.id})")
    result = UserResponse.model_validate(user)
    return success_response(data=result, message="Profile retrieved")


@router.put("/me")
async def update_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    result = await service.update_user(user, data)
    return success_response(data=result, message="Profile updated")


@router.delete("/me")
async def deactivate_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    result = await service.deactivate_user(user)
    return success_response(data=result, message="Account deactivated")


@router.get("/me/stats")
async def get_user_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return dashboard stats: hours_studied, day_streak, topics_mastered, avg_score, weekly_hours."""
    service = UserService(db)
    stats = await service.get_stats(user.id)
    return success_response(data=stats, message="Stats retrieved")


# ── 2FA / TOTP ──────────────────────────────────────────────────────────

@router.post("/me/2fa/setup")
async def setup_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and return QR code for authenticator app setup."""
    if user.is_2fa_enabled:
        raise BadRequestException("2FA is already enabled")
    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.flush()

    uri = get_totp_provisioning_uri(secret, user.email)
    qr_base64 = generate_qr_code_base64(uri)

    return success_response(
        data={
            "secret": secret,
            "provisioning_uri": uri,
            "qr_code_base64": qr_base64,
        },
        message="Scan the QR code with your authenticator app, then confirm with /2fa/confirm",
    )


class TOTPConfirm(BaseModel):
    totp_code: str


@router.post("/me/2fa/confirm")
async def confirm_2fa(
    data: TOTPConfirm,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm 2FA setup by verifying a TOTP code from the authenticator app."""
    if not user.totp_secret:
        raise BadRequestException("2FA setup not initiated — call /2fa/setup first")
    if user.is_2fa_enabled:
        raise BadRequestException("2FA is already enabled")

    if not verify_totp_code(user.totp_secret, data.totp_code):
        raise BadRequestException("Invalid TOTP code")

    user.is_2fa_enabled = True
    await db.flush()
    return success_response(
        data={"message": "2FA enabled successfully", "is_2fa_enabled": True},
        message="2FA enabled successfully",
    )


@router.post("/me/2fa/disable")
async def disable_2fa(
    data: TOTPConfirm,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA by verifying a TOTP code."""
    if not user.is_2fa_enabled:
        raise BadRequestException("2FA is not enabled")

    if not verify_totp_code(user.totp_secret, data.totp_code):
        raise BadRequestException("Invalid TOTP code")

    user.is_2fa_enabled = False
    user.totp_secret = None
    await db.flush()
    return success_response(
        data={"message": "2FA disabled successfully", "is_2fa_enabled": False},
        message="2FA disabled successfully",
    )
