"""Adzuna job board API integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger
from app.services.job_sources.base import BaseJobSource

logger = get_logger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
ADZUNA_COUNTRY = "us"  # default country; can be overridden per-call


class AdzunaJobSource(BaseJobSource):
    """Fetches jobs from the Adzuna REST API."""

    source_name = "adzuna"

    def __init__(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        country: str = ADZUNA_COUNTRY,
    ) -> None:
        super().__init__()
        self.app_id = app_id or settings.ADZUNA_API_ID
        self.api_key = api_key or settings.ADZUNA_API_KEY
        self.country = country

    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Call the Adzuna Jobs Search API.

        Docs: https://developer.adzuna.com/docs/search
        """
        page = kwargs.get("page", 1)
        params: dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "results_per_page": min(limit, 50),
            "what": query,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        if kwargs.get("salary_min"):
            params["salary_min"] = kwargs["salary_min"]
        if kwargs.get("full_time"):
            params["full_time"] = 1

        url = f"{ADZUNA_BASE_URL}/{self.country}/search/{page}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(
                            "Adzuna API error",
                            extra={"status": resp.status, "body": text[:200]},
                        )
                        return []
                    data = await resp.json()
                    return data.get("results", [])
            except aiohttp.ClientError as exc:
                logger.error("Adzuna fetch failed", extra={"error": str(exc)})
                return []

    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map Adzuna result fields to the unified schema."""
        salary_min = self._safe_float(raw.get("salary_min"))
        salary_max = self._safe_float(raw.get("salary_max"))

        # Adzuna returns salary as annual
        description = self._safe_str(raw.get("description"), max_len=10000)
        location_obj = raw.get("location", {})
        location_display = (
            ", ".join(location_obj.get("display_name", "").split(", ")[:2])
            if isinstance(location_obj, dict)
            else self._safe_str(location_obj)
        )

        posted_raw = raw.get("created")
        posted_at: Optional[datetime] = None
        if posted_raw:
            try:
                posted_at = datetime.fromisoformat(posted_raw.rstrip("Z")).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, AttributeError):
                pass

        contract_type = raw.get("contract_type", "")
        job_type = self._normalize_job_type(contract_type)

        category = raw.get("category", {})
        cat_tag = category.get("tag", "") if isinstance(category, dict) else ""

        return {
            "source": self.source_name,
            "external_id": self._safe_str(raw.get("id")),
            "title": self._safe_str(raw.get("title"), max_len=512) or "Untitled",
            "company": self._safe_str(
                raw.get("company", {}).get("display_name") if isinstance(raw.get("company"), dict) else raw.get("company"),
                max_len=255,
            ) or "Unknown",
            "location": location_display,
            "description": description,
            "requirements": None,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_type": job_type,
            "remote": self._detect_remote(f"{description or ''} {location_display or ''}"),
            "url": self._safe_str(raw.get("redirect_url"), max_len=2048),
            "posted_at": posted_at,
            "metadata": {
                "category": cat_tag,
                "contract_time": raw.get("contract_time"),
                "adref": raw.get("adref"),
            },
        }
