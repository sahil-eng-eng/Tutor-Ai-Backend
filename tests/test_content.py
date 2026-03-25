"""Tests for content generation and notes endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestContent:
    SESSION_PAYLOAD = {
        "user_profession": "competitive_exams",
        "concept_name": "Photosynthesis",
        "study_level": "basic",
        "entire_session_type": "basic_overview",
        "session_mode": "single_session",
        "duration_type": "user_defined",
        "duration_minutes": 30,
        "mood": "curious",
        "model_personality": "storyteller",
        "language": "English",
    }

    async def _create_session(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        return resp.json()["data"]["id"]

    async def test_get_content(self, authenticated_client: AsyncClient):
        session_id = await self._create_session(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/content/{session_id}"
        )
        assert resp.status_code == 200

    async def test_generate_content(self, authenticated_client: AsyncClient):
        session_id = await self._create_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/content/{session_id}/generate"
        )
        assert resp.status_code in (200, 201)

    async def test_generate_notes(self, authenticated_client: AsyncClient):
        session_id = await self._create_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/content/{session_id}/notes"
        )
        assert resp.status_code in (200, 201)
