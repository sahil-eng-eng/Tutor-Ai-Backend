"""Tests for user profile endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestUsers:
    async def test_get_profile_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code in (401, 403)

    async def test_get_profile(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "email" in body["data"]
        assert "full_name" in body["data"]

    async def test_update_profile(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.put(
            "/api/v1/users/me",
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Updated Name"

    async def test_deactivate_account(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete("/api/v1/users/me")
        assert resp.status_code == 200
