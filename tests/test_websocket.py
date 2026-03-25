"""Tests for WebSocket session endpoint."""

import pytest
import json
from httpx import ASGITransport, AsyncClient

from app.main import create_application as create_app
from app.database import get_db
from tests.conftest import override_get_db
from app.core.jwt_handler import create_access_token


@pytest.mark.asyncio
class TestWebSocket:
    async def test_websocket_ping_pong(self):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db

        token = create_access_token(data={"sub": "ws-test-user"})
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/ws/session/test-session-id") as ws:
                # Authenticate
                ws.send_text(json.dumps({"action": "authenticate", "token": token}))
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "authenticated"
                assert resp["user_id"] == "ws-test-user"

                # Ping
                ws.send_text(json.dumps({"action": "ping"}))
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "pong"

    async def test_websocket_unauthenticated_action(self):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db

        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/ws/session/test-session-id") as ws:
                ws.send_text(json.dumps({"action": "chat", "message": "Hello"}))
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "error"
                assert "Not authenticated" in resp["message"]

    async def test_websocket_invalid_json(self):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db

        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/ws/session/test-session-id") as ws:
                ws.send_text("not json at all")
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "error"
                assert "Invalid JSON" in resp["message"]

    async def test_websocket_hand_raise(self):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db

        token = create_access_token(data={"sub": "ws-test-user"})
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/ws/session/test-session-id") as ws:
                ws.send_text(json.dumps({"action": "authenticate", "token": token}))
                ws.receive_text()  # authenticated response

                ws.send_text(
                    json.dumps({"action": "hand_raise", "timestamp": 120})
                )
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "hand_raise_ack"
                assert resp["session_paused"] is True

    async def test_websocket_unknown_action(self):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db

        token = create_access_token(data={"sub": "ws-test-user"})
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/ws/session/test-session-id") as ws:
                ws.send_text(json.dumps({"action": "authenticate", "token": token}))
                ws.receive_text()

                ws.send_text(json.dumps({"action": "nonexistent_action"}))
                resp = json.loads(ws.receive_text())
                assert resp["type"] == "error"
                assert "Unknown action" in resp["message"]
