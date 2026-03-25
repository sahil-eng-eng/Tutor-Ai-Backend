"""Tests for the health endpoint and app startup."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"

    async def test_root_redirect_or_docs(self, client: AsyncClient):
        resp = await client.get("/")
        # Should be 200 (docs) or 404 (no root route), not 500
        assert resp.status_code in (200, 307, 404)
