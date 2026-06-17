"""Remotive remote jobs API integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from app.core.logging import get_logger
from app.services.job_sources.base import BaseJobSource

logger = get_logger(__name__)

REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveJobSource(BaseJobSource):
    """Fetches remote jobs from the Remotive public API (no auth required)."""

    source_name = "remotive"

    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Query Remotive's job feed API.

        Docs: https://remotive.com/api/remote-jobs
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if query:
            params["search"] = query
        if kwargs.get("category"):
            params["category"] = kwargs["category"]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    REMOTIVE_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "Remotive API error",
                            extra={"status": resp.status, "body": body[:200]},
                        )
                        return []
                    data = await resp.json()
                    return data.get("jobs", [])[:limit]
            except aiohttp.ClientError as exc:
                logger.error("Remotive fetch failed", extra={"error": str(exc)})
                return []

    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map Remotive fields to the unified schema."""
        posted_at: Optional[datetime] = None
        pub_date = raw.get("publication_date")
        if pub_date:
            try:
                posted_at = datetime.fromisoformat(pub_date.rstrip("Z")).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, AttributeError):
                pass

        salary_str = raw.get("salary", "")
        salary_min, salary_max = self._parse_salary(salary_str)

        description = self._safe_str(raw.get("description"), max_len=10000)
        job_type = self._normalize_job_type(raw.get("job_type", "full_time"))

        return {
            "source": self.source_name,
            "external_id": self._safe_str(raw.get("id")),
            "title": self._safe_str(raw.get("title"), max_len=512) or "Untitled",
            "company": self._safe_str(raw.get("company_name"), max_len=255) or "Unknown",
            "location": self._safe_str(raw.get("candidate_required_location")) or "Remote",
            "description": description,
            "requirements": None,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_type": job_type or "full_time",
            "remote": True,  # all Remotive jobs are remote
            "url": self._safe_str(raw.get("url"), max_len=2048),
            "posted_at": posted_at,
            "metadata": {
                "category": raw.get("category"),
                "tags": raw.get("tags", []),
                "company_logo": raw.get("company_logo"),
            },
        }
