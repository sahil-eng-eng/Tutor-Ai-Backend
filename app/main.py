from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.exception_handlers import register_exception_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.schemas.response import success_response


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Tutor Platform - Delivering highest quality learning with a humanly AI tutor",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Exception handlers (must be registered before middleware)
    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(api_router, prefix="/api/v1")

    @application.get("/health", tags=["Health"])
    async def health_check():
        return success_response(
            data={"status": "healthy", "version": settings.APP_VERSION},
            message="Service is healthy",
        )

    return application


app = create_application()
