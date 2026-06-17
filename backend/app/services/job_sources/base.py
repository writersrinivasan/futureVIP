"""Abstract base class for all job data source integrations."""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, Optional


class BaseJobSource(abc.ABC):
    """
    Abstract base that all job-source adapters must implement.

    Each adapter is responsible for:
    1. Fetching raw job data from its upstream API.
    2. Normalising the raw data into the platform's unified job schema.
    """

    #: Human-readable source identifier stored in ``jobs.source``
    source_name: str = "unknown"

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch raw job listings from the upstream source.

        Args:
            query:    Search query (e.g. "python developer").
            location: Optional geographic filter.
            limit:    Maximum number of results to return.
            **kwargs: Source-specific extra parameters.

        Returns:
            A list of raw job dicts in the source's native format.
        """

    @abc.abstractmethod
    def normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Transform a raw job dict into the platform's unified schema.

        Required output keys:
            source, external_id, title, company, location, description,
            requirements, salary_min, salary_max, job_type, remote, url,
            posted_at

        Args:
            raw: A single raw job dict from ``fetch_jobs``.

        Returns:
            Normalised job dict ready for database insertion.
        """

    # ------------------------------------------------------------------
    # Helpers available to all sub-classes
    # ------------------------------------------------------------------

    def _utcnow(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def _safe_float(self, value: Any) -> Optional[float]:
        """Convert a value to float, returning None on failure."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_str(self, value: Any, max_len: Optional[int] = None) -> Optional[str]:
        """Convert a value to a string, with optional truncation."""
        if value is None:
            return None
        text = str(value).strip()
        if max_len and len(text) > max_len:
            text = text[:max_len]
        return text or None

    def _parse_salary(
        self, salary_str: Any
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Attempt to parse a salary string like "$80,000 - $120,000" into
        a (min, max) float tuple.  Returns (None, None) on failure.
        """
        if not salary_str:
            return None, None
        import re

        numbers = re.findall(r"[\d,]+", str(salary_str))
        values = []
        for n in numbers:
            try:
                values.append(float(n.replace(",", "")))
            except ValueError:
                pass
        if len(values) == 0:
            return None, None
        if len(values) == 1:
            return values[0], values[0]
        return min(values), max(values)

    def _detect_remote(self, text: str) -> bool:
        """Return True when the text indicates a remote position."""
        lower = (text or "").lower()
        return any(
            kw in lower for kw in ("remote", "work from home", "wfh", "distributed", "anywhere")
        )

    def _normalize_job_type(self, raw_type: Any) -> Optional[str]:
        """Map a raw job-type string to the platform's enum values."""
        if raw_type is None:
            return None
        lower = str(raw_type).lower()
        if "full" in lower:
            return "full_time"
        if "part" in lower:
            return "part_time"
        if "contract" in lower:
            return "contract"
        if "freelance" in lower:
            return "freelance"
        if "intern" in lower:
            return "internship"
        if "temp" in lower:
            return "temporary"
        return None

    async def fetch_and_normalize(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Convenience method: fetch raw jobs then normalise each one.

        Silently skips any item that raises an exception during normalisation.
        """
        raw_jobs = await self.fetch_jobs(query, location, limit, **kwargs)
        normalised: list[dict[str, Any]] = []
        for raw in raw_jobs:
            try:
                normalised.append(self.normalize_job(raw))
            except Exception:
                pass  # malformed entries are silently dropped
        return normalised

    # ------------------------------------------------------------------
    # Unified schema reference (for documentation purposes)
    # ------------------------------------------------------------------

    UNIFIED_SCHEMA: dict[str, Any] = {
        "source": str,           # Source identifier, e.g. "adzuna"
        "external_id": str,      # Source-native job ID
        "title": str,            # Job title
        "company": str,          # Company / employer name
        "location": str,         # Location string (city, country, "Remote")
        "description": str,      # Full job description
        "requirements": str,     # Parsed requirements / qualifications
        "salary_min": float,     # Minimum salary (annual, USD)
        "salary_max": float,     # Maximum salary (annual, USD)
        "job_type": str,         # Enum: full_time | part_time | contract | …
        "remote": bool,          # True if remote-friendly
        "url": str,              # Direct link to the job posting
        "posted_at": datetime,   # When the job was originally posted
    }
