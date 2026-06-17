"""RemoteOK API integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from app.core.logging import get_logger
from app.services.job_sources.base import BaseJobSource

logger = get_logger(__name__)

REMOTEOK_API_URL = "https://remoteok.com/api"


class RemoteOKJobSource(BaseJobSource):
    """
    Fetches remote jobs from RemoteOK's public JSON API.

    No API key required.  Rate-limit: be respectful — RemoteOK asks that
    consumers cache for at least 60 minutes.
    """

    source_name = "remoteok"

    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch all remote jobs from RemoteOK and filter by query client-side.

        The API does not support server-side query filtering.
        """
        headers = {
            "User-Agent": "FutureVIP-Career-Platform/1.0 (contact: support@futurevip.io)"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(
                    REMOTEOK_API_URL,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "RemoteOK API error",
                            extra={"status": resp.status, "body": body[:200]},
                        )
                        return []

                    data = await resp.json(content_type=None)
                    # First element is a legal notice dict — skip it
                    jobs = [item for item in data if isinstance(item, dict) and item.get("id")]

            except aiohttp.ClientError as exc:
                logger.error("RemoteOK fetch failed", extra={"error": str(exc)})
                return []

        # Client-side keyword filter
        if query:
            query_lower = query.lower()
            jobs = [
                j
                for j in jobs
                if query_lower in (j.get("position") or "").lower()
                or query_lower in (j.get("company") or "").lower()
                or any(query_lower in tag.lower() for tag in j.get("tags", []))
            ]

        return jobs[:limit]

    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map RemoteOK fields to the unified schema."""
        posted_at: Optional[datetime] = None
        epoch = raw.get("epoch")
        if epoch:
            try:
                posted_at = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            except (ValueError, OSError):
                pass

        description = self._safe_str(raw.get("description"), max_len=10000)
        tags = raw.get("tags", [])
        slug = raw.get("slug", "")
        url = f"https://remoteok.com/remote-jobs/{slug}" if slug else None

        return {
            "source": self.source_name,
            "external_id": self._safe_str(raw.get("id")),
            "title": self._safe_str(raw.get("position"), max_len=512) or "Untitled",
            "company": self._safe_str(raw.get("company"), max_len=255) or "Unknown",
            "location": "Remote",
            "description": description,
            "requirements": None,
            "salary_min": self._safe_float(raw.get("salary_min")),
            "salary_max": self._safe_float(raw.get("salary_max")),
            "job_type": "full_time",
            "remote": True,
            "url": self._safe_str(url, max_len=2048),
            "posted_at": posted_at,
            "metadata": {
                "tags": tags,
                "logo": raw.get("logo"),
                "views": raw.get("views"),
                "applications": raw.get("applications"),
            },
        }
