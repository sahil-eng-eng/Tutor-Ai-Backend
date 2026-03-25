"""
Shared test fixtures for the AI Tutor Platform.
Uses an in-memory SQLite async database for isolation.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import Base
from app.database import get_db
from app.main import create_application as create_app

# Force test settings
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-automated-testing-only"
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key"
os.environ["ELEVENLABS_API_KEY"] = "test-elevenlabs-key"
os.environ["ENVIRONMENT"] = "testing"

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """Register and login a test user, return client with auth header."""
    user_data = {
        "email": f"testuser_{uuid.uuid4().hex[:8]}@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "user_type": "college_student",
    }
    await client.post("/api/v1/auth/register", json=user_data)

    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    tokens = login_resp.json()
    access_token = tokens.get("data", {}).get("tokens", {}).get("access_token", "")
    client.headers["Authorization"] = f"Bearer {access_token}"
    return client
