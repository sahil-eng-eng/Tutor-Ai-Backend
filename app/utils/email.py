"""
Email utility — placeholder for future email service integration.
"""

import logging

logger = logging.getLogger("ai_tutor")


async def send_verification_email(email: str, otp_code: str) -> bool:
    """
    Send a verification email with OTP code.

    NOTE: This is a placeholder. Integrate with an actual email service
    (SendGrid, AWS SES, Mailgun, etc.) in production.
    """
    logger.info(
        "PLACEHOLDER: Verification email to %s with code %s",
        email,
        otp_code,
    )
    # In production, implement actual email sending here.
    # Example with SendGrid:
    # from sendgrid import SendGridAPIClient
    # message = Mail(
    #     from_email="noreply@aitutor.com",
    #     to_emails=email,
    #     subject="Verify your AI Tutor account",
    #     html_content=f"<p>Your verification code is: <strong>{otp_code}</strong></p>"
    # )
    # sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    # sg.send(message)
    return True


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Placeholder for password reset email."""
    logger.info("PLACEHOLDER: Password reset email to %s", email)
    return True
