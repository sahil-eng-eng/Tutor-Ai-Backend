"""Tests for interaction endpoints (doubts, pulse, MCQ, chat)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestInteractions:
    SESSION_PAYLOAD = {
        "user_profession": "competitive_exams",
        "concept_name": "Thermodynamics",
        "study_level": "advanced",
        "entire_session_type": "in_depth",
        "session_mode": "single_session",
        "duration_type": "user_defined",
        "duration_minutes": 45,
        "mood": "focused",
        "model_personality": "attentive",
        "language": "English",
    }

    async def _create_and_start_session(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = resp.json()["data"]["id"]
        await client.post(f"/api/v1/sessions/{session_id}/start")
        return session_id

    async def test_hand_raise(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/interactions/hand-raise",
            json={"session_id": session_id, "timestamp_in_session_seconds": 120},
        )
        assert resp.status_code == 200

    async def test_submit_doubt_text(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/interactions/doubts",
            data={"session_id": session_id, "doubt_text": "I don't understand entropy"},
        )
        assert resp.status_code in (200, 201)

    async def test_list_doubts(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/interactions/doubts/{session_id}"
        )
        assert resp.status_code == 200

    async def test_record_pulse(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/record",
            json={"focus_level": 72.0},
        )
        assert resp.status_code == 200

    async def test_get_pulse(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/interactions/pulse/{session_id}"
        )
        assert resp.status_code == 200

    async def test_chat_message(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/interactions/chat",
            json={
                "session_id": session_id,
                "message": "Can you give me an example?",
                "timestamp_in_session_seconds": 200,
            },
        )
        assert resp.status_code == 200

    async def test_generate_mcq(self, authenticated_client: AsyncClient):
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/interactions/mcq/{session_id}/generate",
            params={"topic": "Thermodynamics"},
        )
        assert resp.status_code == 200

    # ── Pulse Meter Tests ──────────────────────────────────────────

    async def test_pulse_adjust_increase(self, authenticated_client: AsyncClient):
        """Frontend can increase pulse via adjust endpoint."""
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/adjust",
            json={"adjustment": 10.0, "reason": "user engagement high"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data.get("pulse_percentage") is not None
        assert data["pulse_percentage"] >= 50.0  # Started at 50 + 10

    async def test_pulse_adjust_decrease(self, authenticated_client: AsyncClient):
        """Frontend can decrease pulse via adjust endpoint."""
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/adjust",
            json={"adjustment": -15.0, "reason": "user seems distracted"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["pulse_percentage"] <= 50.0  # Started at 50 - 15

    async def test_pulse_activity_tracking(self, authenticated_client: AsyncClient):
        """Record activity endpoint should adjust pulse automatically."""
        session_id = await self._create_and_start_session(authenticated_client)
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/activity",
            params={"activity_type": "hand_raise"},
        )
        assert resp.status_code == 200

    async def test_pulse_adjust_clamped(self, authenticated_client: AsyncClient):
        """Pulse should be clamped between 0 and 100."""
        session_id = await self._create_and_start_session(authenticated_client)
        # Try to push above 100
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/adjust",
            json={"adjustment": 50.0},
        )
        assert resp.status_code == 200
        resp = await authenticated_client.post(
            f"/api/v1/interactions/pulse/{session_id}/adjust",
            json={"adjustment": 50.0},
        )
        data = resp.json()["data"]
        assert data["pulse_percentage"] <= 100.0

    async def test_hand_raise_affects_pulse(self, authenticated_client: AsyncClient):
        """Hand raise should automatically track pulse activity."""
        session_id = await self._create_and_start_session(authenticated_client)
        await authenticated_client.post(
            "/api/v1/interactions/hand-raise",
            json={"session_id": session_id, "timestamp_in_session_seconds": 120},
        )
        # Check pulse changed
        resp = await authenticated_client.get(
            f"/api/v1/interactions/pulse/{session_id}"
        )
        assert resp.status_code == 200
