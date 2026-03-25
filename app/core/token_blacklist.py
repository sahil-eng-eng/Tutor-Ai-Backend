"""
Token Blacklist — Redis-based JWT blacklist for secure logout.
Stores invalidated JTIs (JWT IDs) with TTL matching token expiry.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("ai_tutor")

# Module-level reference to avoid import cycles
_redis_client = None


async def _get_redis():
    """Lazy-init Redis client."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis
        from app.config import settings

        _redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable — token blacklist disabled")
        return None


async def blacklist_token(jti: str, ttl_seconds: int) -> bool:
    """Add a token JTI to the blacklist with a TTL."""
    r = await _get_redis()
    if r is None:
        return False
    try:
        await r.setex(f"blacklist:{jti}", ttl_seconds, "1")
        return True
    except Exception:
        logger.exception("Failed to blacklist token %s", jti)
        return False


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI has been blacklisted."""
    r = await _get_redis()
    if r is None:
        return False
    try:
        result = await r.get(f"blacklist:{jti}")
        return result is not None
    except Exception:
        logger.exception("Failed to check blacklist for %s", jti)
        return False
