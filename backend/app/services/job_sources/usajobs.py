"""USAJobs.gov API integration for US Federal Government jobs."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from app.core.logging import get_logger
from app.services.job_sources.base import BaseJobSource

logger = get_logger(__name__)

USAJOBS_BASE_URL = "https://data.usajobs.gov/api/search"
USAJOBS_EMAIL = os.getenv("USAJOBS_EMAIL", "support@futurevip.io")
USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")


class USAJobsSource(BaseJobSource):
    """
    Fetches US Federal Government job listings from the USAJobs API.

    Docs: https://developer.usajobs.gov/API-Reference/GET-api-Search
    """

    source_name = "usajobs"

    def __init__(
        self,
        api_key: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.api_key = api_key or USAJOBS_API_KEY
        self.user_email = user_email or USAJOBS_EMAIL

    def _headers(self) -> dict[str, str]:
        return {
            "Host": "data.usajobs.gov",
            "User-Agent": self.user_email,
            "Authorization-Key": self.api_key,
        }

    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Call the USAJobs search endpoint."""
        params: dict[str, Any] = {
            "Keyword": query,
            "ResultsPerPage": min(limit, 500),
            "Fields": "Min",
        }
        if location:
            params["LocationName"] = location
        if kwargs.get("pay_grade_low"):
            params["PayGradeLow"] = kwargs["pay_grade_low"]
        if kwargs.get("pay_grade_high"):
            params["PayGradeHigh"] = kwargs["pay_grade_high"]
        if kwargs.get("remote_indicator"):
            params["RemoteIndicator"] = kwargs["remote_indicator"]

        async with aiohttp.ClientSession(headers=self._headers()) as session:
            try:
                async with session.get(
                    USAJOBS_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "USAJobs API error",
                            extra={"status": resp.status, "body": body[:300]},
                        )
                        return []
                    data = await resp.json()
                    search_result = data.get("SearchResult", {})
                    items = search_result.get("SearchResultItems", [])
                    return items[:limit]
            except aiohttp.ClientError as exc:
                logger.error("USAJobs fetch failed", extra={"error": str(exc)})
                return []

    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map USAJobs SearchResultItem fields to the unified schema."""
        match_data = raw.get("MatchedObjectDescriptor", {})
        position_id = raw.get("MatchedObjectId", "")

        # Salary
        remuneration = match_data.get("PositionRemuneration", [{}])
        rem = remuneration[0] if remuneration else {}
        salary_min = self._safe_float(rem.get("MinimumRange"))
        salary_max = self._safe_float(rem.get("MaximumRange"))

        # Dates
        posted_at: Optional[datetime] = None
        pub_start = match_data.get("PublicationStartDate")
        if pub_start:
            try:
                posted_at = datetime.fromisoformat(pub_start.rstrip("Z")).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, AttributeError):
                pass

        # Location
        locations = match_data.get("PositionLocation", [{}])
        loc = locations[0] if locations else {}
        city = loc.get("CityName", "")
        state_code = loc.get("CountrySubDivisionCode", "")
        location = f"{city}, {state_code}".strip(", ") or None

        # Remote detection
        telework_eligible = match_data.get("PositionOfferingType", [])
        is_remote = any(
            "remote" in str(t).lower() or "telework" in str(t).lower()
            for t in telework_eligible
        ) or self._detect_remote(f"{match_data.get('QualificationSummary', '')} {location or ''}")

        # Description
        description = self._safe_str(
            match_data.get("UserArea", {}).get("Details", {}).get("JobSummary")
            or match_data.get("QualificationSummary"),
            max_len=10000,
        )

        # Job type
        schedule_type = match_data.get("PositionSchedule", [{}])
        raw_type = schedule_type[0].get("Name", "") if schedule_type else ""
        job_type = self._normalize_job_type(raw_type) or "full_time"

        apply_uri = match_data.get("ApplyURI", [""])[0] if match_data.get("ApplyURI") else None
        position_uri = match_data.get("PositionURI", apply_uri)

        return {
            "source": self.source_name,
            "external_id": self._safe_str(position_id),
            "title": self._safe_str(match_data.get("PositionTitle"), max_len=512) or "Untitled",
            "company": self._safe_str(match_data.get("OrganizationName"), max_len=255) or "US Government",
            "location": location,
            "description": description,
            "requirements": self._safe_str(
                match_data.get("QualificationSummary"), max_len=5000
            ),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_type": job_type,
            "remote": is_remote,
            "url": self._safe_str(position_uri or apply_uri, max_len=2048),
            "posted_at": posted_at,
            "metadata": {
                "department": match_data.get("DepartmentName"),
                "security_clearance": match_data.get("SecurityClearance"),
                "hiring_path": match_data.get("HiringPath", []),
                "position_id": position_id,
            },
        }
