"""JSearch (RapidAPI) job search integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger
from app.services.job_sources.base import BaseJobSource

logger = get_logger(__name__)

JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"


class JSearchJobSource(BaseJobSource):
    """Fetches jobs via the JSearch API on RapidAPI."""

    source_name = "jsearch"

    def __init__(self, api_key: Optional[str] = None) -> None:
        super().__init__()
        self.api_key = api_key or settings.JSEARCH_API_KEY

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }

    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Query the JSearch API.

        Docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
        """
        search_query = query
        if location:
            search_query = f"{query} in {location}"

        params: dict[str, Any] = {
            "query": search_query,
            "page": kwargs.get("page", "1"),
            "num_pages": "1",
        }
        if kwargs.get("date_posted"):
            params["date_posted"] = kwargs["date_posted"]
        if kwargs.get("employment_types"):
            params["employment_types"] = kwargs["employment_types"]
        if kwargs.get("remote_jobs_only"):
            params["remote_jobs_only"] = "true"

        async with aiohttp.ClientSession(headers=self._headers()) as session:
            try:
                async with session.get(
                    JSEARCH_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "JSearch API error",
                            extra={"status": resp.status, "body": body[:300]},
                        )
                        return []
                    data = await resp.json()
                    return data.get("data", [])[:limit]
            except aiohttp.ClientError as exc:
                logger.error("JSearch fetch failed", extra={"error": str(exc)})
                return []

    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map JSearch fields to the unified schema."""
        # Salary
        min_salary = self._safe_float(raw.get("job_min_salary"))
        max_salary = self._safe_float(raw.get("job_max_salary"))
        salary_period = raw.get("job_salary_period", "").upper()
        # Convert hourly → annual estimate
        if salary_period == "HOUR":
            if min_salary:
                min_salary = min_salary * 2080
            if max_salary:
                max_salary = max_salary * 2080

        # Dates
        posted_at: Optional[datetime] = None
        posted_ts = raw.get("job_posted_at_timestamp")
        if posted_ts:
            try:
                posted_at = datetime.fromtimestamp(int(posted_ts), tz=timezone.utc)
            except (ValueError, OSError):
                pass

        # Employment type
        emp_type = raw.get("job_employment_type", "")
        job_type = self._normalize_job_type(emp_type)

        # Location
        city = raw.get("job_city") or ""
        state = raw.get("job_state") or ""
        country = raw.get("job_country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) or None

        is_remote = bool(raw.get("job_is_remote")) or self._detect_remote(
            f"{raw.get('job_title', '')} {raw.get('job_description', '')}"
        )

        description = self._safe_str(raw.get("job_description"), max_len=10000)
        highlights = raw.get("job_highlights", {}) or {}
        qualifications = highlights.get("Qualifications", [])
        requirements = "\n".join(qualifications) if qualifications else None

        return {
            "source": self.source_name,
            "external_id": self._safe_str(raw.get("job_id")),
            "title": self._safe_str(raw.get("job_title"), max_len=512) or "Untitled",
            "company": self._safe_str(raw.get("employer_name"), max_len=255) or "Unknown",
            "location": location,
            "description": description,
            "requirements": requirements,
            "salary_min": min_salary,
            "salary_max": max_salary,
            "job_type": job_type,
            "remote": is_remote,
            "url": self._safe_str(raw.get("job_apply_link"), max_len=2048),
            "posted_at": posted_at,
            "metadata": {
                "employer_logo": raw.get("employer_logo"),
                "job_publisher": raw.get("job_publisher"),
                "job_onet_soc": raw.get("job_onet_soc"),
                "benefits": highlights.get("Benefits", []),
            },
        }
