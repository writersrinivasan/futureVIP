"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        await client.post("/api/v1/auth/register", json=test_user_data)
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "Pass123!", "full_name": "Test"},
        )
        assert response.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "weak", "full_name": "Test"},
        )
        assert response.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user_data: dict):
        await client.post("/api/v1/auth/register", json=test_user_data)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict):
        await client.post("/api/v1/auth/register", json=test_user_data)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": "WrongPass999!"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Pass123!"},
        )
        assert response.status_code == 401

    async def test_login_invalid_payload(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestProtectedEndpoints:
    async def _get_token(self, client: AsyncClient, test_user_data: dict) -> str:
        await client.post("/api/v1/auth/register", json=test_user_data)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        return response.json()["access_token"]

    async def test_get_me_authenticated(self, client: AsyncClient, test_user_data: dict):
        token = await self._get_token(client, test_user_data)
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401

    async def test_refresh_token(self, client: AsyncClient, test_user_data: dict):
        await client.post("/api/v1/auth/register", json=test_user_data)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        refresh_token = login_resp.json()["refresh_token"]
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


@pytest.mark.asyncio
class TestHealthEndpoints:
    async def test_health_liveness(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_api_health(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
