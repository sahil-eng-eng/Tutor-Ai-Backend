"""Tests for session management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSessions:
    SESSION_PAYLOAD = {
        "user_profession": "competitive_exams",
        "concept_name": "Quadratic Equations",
        "study_level": "intermediate",
        "entire_session_type": "intermediate",
        "session_mode": "single_session",
        "duration_type": "user_defined",
        "duration_minutes": 30,
        "mood": "focused",
        "model_personality": "very_friendly",
        "language": "English",
    }

    async def test_create_session(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/sessions",
            json=self.SESSION_PAYLOAD,
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["concept_name"] == "Quadratic Equations"
        assert "id" in data

    async def test_list_sessions(self, authenticated_client: AsyncClient):
        await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        resp = await authenticated_client.get("/api/v1/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "sessions" in body["data"]

    async def test_list_sessions_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code in (401, 403)

    async def test_get_session_detail(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        resp = await authenticated_client.get(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == 200

    async def test_start_session(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        assert resp.status_code == 200

    async def test_pause_session(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/pause")
        assert resp.status_code == 200

    async def test_complete_session(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/complete")
        assert resp.status_code == 200

    async def test_cancel_session(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/cancel")
        assert resp.status_code == 200

    async def test_update_session_config(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/sessions", json=self.SESSION_PAYLOAD
        )
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        resp = await authenticated_client.patch(
            f"/api/v1/sessions/{session_id}/config",
            json={"mood": "very_focused", "personality": "motivational"},
        )
        assert resp.status_code == 200

    async def test_get_nonexistent_session(self, authenticated_client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await authenticated_client.get(f"/api/v1/sessions/{fake_id}")
        assert resp.status_code == 404

    # ── New Feature Tests ──────────────────────────────────────────

    async def test_create_session_has_evaluation(self, authenticated_client: AsyncClient):
        """Session creation should include session_evaluation (from AI or fallback)."""
        resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert data.get("session_evaluation") is not None
        evaluation = data["session_evaluation"]
        assert "session_overview" in evaluation
        assert "segments" in evaluation

    async def test_create_session_draft_status(self, authenticated_client: AsyncClient):
        """New sessions should be created in DRAFT status (not READY)."""
        resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert data["status"] == "draft"

    async def test_create_session_user_profession_stored(self, authenticated_client: AsyncClient):
        """user_profession should be stored and returned."""
        resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        data = resp.json()["data"]
        assert data["user_profession"] == "competitive_exams"

    async def test_create_session_college_student_flow(self, authenticated_client: AsyncClient):
        """College student flow requires university, course, semester."""
        payload = {
            **self.SESSION_PAYLOAD,
            "user_profession": "college_student",
            "university": "MIT",
            "course": "Computer Science",
            "semester": 3,
        }
        resp = await authenticated_client.post("/api/v1/sessions", json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert data["university"] == "MIT"
        assert data["course"] == "Computer Science"
        assert data["semester"] == 3

    async def test_create_session_college_student_missing_fields(self, authenticated_client: AsyncClient):
        """College student flow should fail without required fields."""
        payload = {
            **self.SESSION_PAYLOAD,
            "user_profession": "college_student",
            # Missing university, course, semester
        }
        resp = await authenticated_client.post("/api/v1/sessions", json=payload)
        assert resp.status_code == 422

    async def test_create_session_working_professional_flow(self, authenticated_client: AsyncClient):
        """Working professional flow requires professional_background."""
        payload = {
            **self.SESSION_PAYLOAD,
            "user_profession": "working_professional",
            "professional_background": "Software Engineer with 5 years experience",
        }
        resp = await authenticated_client.post("/api/v1/sessions", json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert data["professional_background"] == "Software Engineer with 5 years experience"

    async def test_create_session_working_professional_missing_fields(self, authenticated_client: AsyncClient):
        """Working professional flow should fail without professional_background."""
        payload = {
            **self.SESSION_PAYLOAD,
            "user_profession": "working_professional",
        }
        resp = await authenticated_client.post("/api/v1/sessions", json=payload)
        assert resp.status_code == 422

    async def test_preview_session(self, authenticated_client: AsyncClient):
        """Preview endpoint should return session_evaluation data."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]

        resp = await authenticated_client.get(f"/api/v1/sessions/{session_id}/preview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["session_id"] == session_id
        assert data["concept_name"] == "Quadratic Equations"
        assert data["session_evaluation"] is not None

    async def test_update_session_evaluation(self, authenticated_client: AsyncClient):
        """Update evaluation endpoint should accept modified evaluation JSON."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]

        updated_eval = {
            "session_overview": {"main_concept": "Updated Concept"},
            "segments": [
                {"segment_order": 1, "title": "Updated Intro", "duration_seconds": 600}
            ],
        }
        resp = await authenticated_client.put(
            f"/api/v1/sessions/{session_id}/evaluation",
            json={"session_evaluation": updated_eval},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["session_evaluation"]["session_overview"]["main_concept"] == "Updated Concept"

    async def test_start_session_creates_segments(self, authenticated_client: AsyncClient):
        """Starting a session should build segment DB rows from evaluation."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]

        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "in_progress"
        assert len(data["segments"]) > 0

    async def test_end_session_with_goodbye(self, authenticated_client: AsyncClient):
        """End session should return a goodbye message."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")

        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/end")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert "goodbye_message" in data
        assert len(data["goodbye_message"]) > 0

    async def test_end_already_completed_session_fails(self, authenticated_client: AsyncClient):
        """Ending an already completed session should fail."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/end")

        resp = await authenticated_client.post(f"/api/v1/sessions/{session_id}/end")
        assert resp.status_code == 400

    async def test_cannot_update_evaluation_after_start(self, authenticated_client: AsyncClient):
        """Cannot update evaluation once session has started."""
        create_resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        session_id = create_resp.json()["data"]["id"]
        await authenticated_client.post(f"/api/v1/sessions/{session_id}/start")

        resp = await authenticated_client.put(
            f"/api/v1/sessions/{session_id}/evaluation",
            json={"session_evaluation": {"session_overview": {}, "segments": []}},
        )
        assert resp.status_code == 400

    async def test_pulse_percentage_default(self, authenticated_client: AsyncClient):
        """Newly created session should have default pulse_percentage of 50.0."""
        resp = await authenticated_client.post("/api/v1/sessions", json=self.SESSION_PAYLOAD)
        data = resp.json()["data"]
        assert data.get("pulse_percentage") == 50.0
