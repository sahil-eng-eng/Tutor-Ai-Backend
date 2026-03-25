"""
WebSocket endpoint for real-time session interaction.
Handles: live teaching stream, hand-raise, chat, pulse updates, config changes.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.jwt_handler import verify_access_token
from app.models.user import User
from app.models.session import TutorSession, SessionStatus
from app.models.interaction import Interaction, InteractionType
from app.prompts.interaction_prompts import (
    DOUBT_ACKNOWLEDGEMENT_RESPONSES,
    DOUBT_RESOLVED_RESPONSES,
    CELEBRATION_RESPONSES,
    SEGMENT_TRANSITION_RESPONSES,
    get_random_response,
)
from app.services.ai_tutor_service import chat_completion

logger = logging.getLogger("ai_tutor")

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per session."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                c for c in self.active_connections[session_id] if c != websocket
            ]
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            payload = json.dumps(message)
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    pass


manager = ConnectionManager()


async def _authenticate_ws(token: str) -> tuple[bool, dict | None]:
    """Authenticate a WebSocket connection via JWT token."""
    payload = verify_access_token(token)
    if not payload:
        return False, None
    return True, payload


@router.websocket("/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time WebSocket for a tutoring session.

    Client sends JSON messages with an "action" field:
    - {"action": "authenticate", "token": "<jwt>"}
    - {"action": "hand_raise", "timestamp": 120}
    - {"action": "chat", "message": "What is X?", "timestamp": 150}
    - {"action": "doubt_resolved", "method": "go_ahead_button"}
    - {"action": "go_ahead"}
    - {"action": "config_change", "changes": {"mood": "focused"}}
    - {"action": "mcq_answer", "question_id": "...", "answer": "A"}
    - {"action": "ping"}

    Server sends JSON messages:
    - {"type": "authenticated", "user_id": "..."}
    - {"type": "teaching", "content": "...", "segment": {...}}
    - {"type": "hand_raise_ack", "message": "..."}
    - {"type": "doubt_response", "answer": "..."}
    - {"type": "doubt_resolved", "message": "..."}
    - {"type": "pulse_update", "pulse": {...}}
    - {"type": "segment_transition", "message": "...", "next_segment": {...}}
    - {"type": "mcq_check", "questions": [...]}
    - {"type": "celebration", "message": "..."}
    - {"type": "config_updated", "changes": {...}}
    - {"type": "error", "message": "..."}
    - {"type": "pong"}
    """
    await manager.connect(websocket, session_id)
    authenticated = False
    user_id = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )
                continue

            action = data.get("action", "")

            # ── Authentication ─────────────────────────────────────
            if action == "authenticate":
                token = data.get("token", "")
                ok, payload = await _authenticate_ws(token)
                if ok and payload:
                    authenticated = True
                    user_id = payload.get("sub")
                    await websocket.send_text(
                        json.dumps({"type": "authenticated", "user_id": user_id})
                    )
                else:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Authentication failed"})
                    )
                continue

            if not authenticated:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Not authenticated. Send authenticate action first."})
                )
                continue

            # ── Ping ───────────────────────────────────────────────
            if action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # ── Hand Raise ─────────────────────────────────────────
            if action == "hand_raise":
                ack = get_random_response(DOUBT_ACKNOWLEDGEMENT_RESPONSES)
                await websocket.send_text(
                    json.dumps({
                        "type": "hand_raise_ack",
                        "message": ack,
                        "session_paused": True,
                    })
                )
                # Record interaction
                async with AsyncSessionLocal() as db:
                    interaction = Interaction(
                        session_id=UUID(session_id),
                        interaction_type=InteractionType.HAND_RAISE,
                        ai_response=ack,
                        timestamp_in_session_seconds=data.get("timestamp"),
                    )
                    db.add(interaction)
                    await db.commit()
                continue

            # ── Chat / Doubt ───────────────────────────────────────
            if action == "chat":
                message = data.get("message", "")
                if not message:
                    continue

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(TutorSession).where(TutorSession.id == UUID(session_id))
                    )
                    session = result.scalar_one_or_none()
                    system_prompt = session.system_prompt_snapshot if session else ""
                    model = session.ai_model_used if session else ""

                try:
                    ai_response = await chat_completion(
                        system_prompt=system_prompt or "",
                        user_message=message,
                        model=model or "",
                    )
                except Exception:
                    ai_response = "Could you rephrase that? I want to make sure I help you properly."

                await websocket.send_text(
                    json.dumps({
                        "type": "doubt_response" if data.get("is_doubt") else "chat_response",
                        "answer": ai_response,
                    })
                )

                # Record
                async with AsyncSessionLocal() as db:
                    interaction = Interaction(
                        session_id=UUID(session_id),
                        interaction_type=InteractionType.DOUBT if data.get("is_doubt") else InteractionType.CHAT,
                        user_message=message,
                        ai_response=ai_response,
                        timestamp_in_session_seconds=data.get("timestamp"),
                    )
                    db.add(interaction)
                    await db.commit()
                continue

            # ── Doubt Resolved / Go Ahead ──────────────────────────
            if action in ("doubt_resolved", "go_ahead"):
                resume_msg = get_random_response(DOUBT_RESOLVED_RESPONSES)
                await websocket.send_text(
                    json.dumps({
                        "type": "doubt_resolved",
                        "message": resume_msg,
                        "session_resumed": True,
                    })
                )
                continue

            # ── Config Change ──────────────────────────────────────
            if action == "config_change":
                changes = data.get("changes", {})
                await websocket.send_text(
                    json.dumps({
                        "type": "config_updated",
                        "changes": changes,
                        "message": "Configuration updated. Adjusting session accordingly.",
                    })
                )
                continue

            # ── MCQ Answer ─────────────────────────────────────────
            if action == "mcq_answer":
                is_correct = data.get("is_correct", False)
                if is_correct:
                    celebration = get_random_response(CELEBRATION_RESPONSES)
                    await websocket.send_text(
                        json.dumps({"type": "celebration", "message": celebration})
                    )
                else:
                    await websocket.send_text(
                        json.dumps({
                            "type": "mcq_feedback",
                            "message": "Not quite right, but that's okay! Let me explain...",
                        })
                    )
                continue

            # Unknown action
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Unknown action: {action}"})
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
        manager.disconnect(websocket, session_id)
