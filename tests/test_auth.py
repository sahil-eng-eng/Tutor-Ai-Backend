"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuth:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "full_name": "New User",
            "user_type": "college_student",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["user"]["email"] == "newuser@example.com"
        assert "tokens" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dup@example.com",
            "password": "StrongPass123!",
            "full_name": "Dup User",
            "user_type": "college_student",
        }
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code in (400, 409)
        assert resp.json()["success"] is False

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weakpw@example.com",
            "password": "123",
            "full_name": "Weak PW",
            "user_type": "college_student",
        })
        assert resp.status_code == 422
        assert resp.json()["success"] is False

    async def test_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "loginuser@example.com",
            "password": "StrongPass123!",
            "full_name": "Login User",
            "user_type": "college_student",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "loginuser@example.com",
            "password": "StrongPass123!",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "tokens" in data
        assert data["tokens"]["access_token"]
        assert data["tokens"]["refresh_token"]

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@example.com",
            "password": "StrongPass123!",
            "full_name": "Wrong PW",
            "user_type": "college_student",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrongpw@example.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "ghost@example.com",
            "password": "Whatever123!",
        })
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    async def test_refresh_token(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
            "full_name": "Refresh User",
            "user_type": "college_student",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
        })
        refresh_token = login_resp.json()["data"]["tokens"]["refresh_token"]
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["access_token"]

    async def test_change_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "chgpw@example.com",
            "password": "StrongPass123!",
            "full_name": "Change PW",
            "user_type": "college_student",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "chgpw@example.com",
            "password": "StrongPass123!",
        })
        token = login_resp.json()["data"]["tokens"]["access_token"]
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
