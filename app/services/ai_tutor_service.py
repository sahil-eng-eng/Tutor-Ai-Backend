"""
AI Tutor Service — orchestrates OpenAI calls for teaching content generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("ai_tutor")

# Lazy client — created on first use
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
    return _client


async def chat_completion(
    *,
    system_prompt: str,
    user_message: str,
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> str:
    """Send a chat completion request to OpenAI."""
    model = model or settings.OPENAI_DEFAULT_MODEL
    client = _get_client()

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    resp = await client.post("/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def chat_completion_with_history(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Send a chat completion with full message history (for ongoing sessions)."""
    model = model or settings.OPENAI_DEFAULT_MODEL
    client = _get_client()

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": model,
        "messages": full_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = await client.post("/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def generate_json_response(
    *,
    system_prompt: str,
    user_message: str,
    model: str = "",
    temperature: float = 0.5,
    max_tokens: int = 8192,
) -> Any:
    """Generate a response that should be valid JSON."""
    raw = await chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("AI response was not valid JSON, returning raw string")
        return raw


async def streaming_chat_completion(
    *,
    system_prompt: str,
    user_message: str,
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """Stream a chat completion — yields text chunks."""
    model = model or settings.OPENAI_DEFAULT_MODEL
    client = _get_client()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    async with client.stream("POST", "/chat/completions", json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
