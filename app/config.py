from __future__ import annotations

from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI_Tutor_Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-min-32-chars-long"
    ALLOWED_HOSTS: str = '["*"]'

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_tutor_db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_CHEAP_MODEL: str = "gpt-4o-mini"
    OPENAI_PREMIUM_MODEL: str = "gpt-4o"

    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"

    # Session
    MAX_SESSION_DURATION_MINUTES: int = 180
    DEFAULT_SESSION_DURATION_MINUTES: int = 60
    MAX_SEGMENTS_PER_SESSION: int = 20

    # Pulse
    PULSE_LOW_THRESHOLD: int = 25
    PULSE_CHECK_INTERVAL_MINUTES: int = 10

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Nano-Banana Image Generation
    NANOBANANA_API_URL: str = ""
    NANOBANANA_API_KEY: str = ""
    NANOBANANA_TIMEOUT_SECONDS: int = 30
    NANOBANANA_ENABLED: bool = True

    # Email / OTP
    EMAIL_SERVICE_ENABLED: bool = False
    OTP_SERVICE_ENABLED: bool = False
    OTP_EXPIRY_MINUTES: int = 10

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8080"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    @property
    def allowed_hosts_list(self) -> List[str]:
        return json.loads(self.ALLOWED_HOSTS)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
