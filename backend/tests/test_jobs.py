"""Integration tests for jobs endpoints."""

import pytest
import uuid
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, user_data: dict) -> str:
    await client.post("/api/v1/auth/register", json=user_data)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
class TestJobsEndpoints:
    async def test_list_jobs_authenticated(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/jobs/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_jobs_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/jobs/")
        assert response.status_code == 401

    async def test_list_jobs_with_filters(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/jobs/",
            params={"remote": True, "job_type": "full_time", "page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_get_nonexistent_job(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        fake_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/jobs/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_search_jobs(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.post(
            "/api/v1/jobs/search",
            json={"query": "Python developer", "location": "Remote"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_get_job_matches_no_resume(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/jobs/matches",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should return empty or 200 with empty items
        assert response.status_code in (200, 404)


@pytest.mark.asyncio
class TestApplicationsEndpoints:
    async def test_list_applications_empty(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/applications/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_create_application_invalid_job(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.post(
            "/api/v1/applications/",
            json={"job_id": str(uuid.uuid4()), "status": "saved"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_application_stats(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/applications/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data


@pytest.mark.asyncio
class TestNotificationsEndpoints:
    async def test_list_notifications_empty(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_mark_all_read(self, client: AsyncClient, test_user_data: dict):
        token = await _register_and_login(client, test_user_data)
        response = await client.put(
            "/api/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
