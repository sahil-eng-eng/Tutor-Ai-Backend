import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("ai_tutor")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        logger.info(
            "method=%s path=%s status=%d duration=%.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        return response
