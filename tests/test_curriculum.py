"""Tests for curriculum management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCurriculum:
    async def test_list_boards(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/curriculum/boards")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    async def test_list_question_banks(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/curriculum/question-banks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    async def test_list_voices(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/voices")
        assert resp.status_code == 200

    async def test_upload_material_no_file(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/api/v1/materials/upload")
        assert resp.status_code == 422
