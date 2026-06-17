"""
Job aggregator service.

Orchestrates fetching from all enabled job sources, deduplicates results,
and persists new jobs to the database.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Job
from app.services.job_sources.adzuna import AdzunaJobSource
from app.services.job_sources.base import BaseJobSource
from app.services.job_sources.jsearch import JSearchJobSource
from app.services.job_sources.remoteok import RemoteOKJobSource
from app.services.job_sources.remotive import RemotiveJobSource
from app.services.job_sources.usajobs import USAJobsSource

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedup_key(job: dict[str, Any]) -> str:
    """
    Generate a stable deduplication hash for a normalised job dict.

    Two jobs are considered duplicates when they share the same
    (title + company + location) after lower-casing and stripping whitespace.
    """
    raw = " ".join(
        [
            (job.get("title") or "").lower().strip(),
            (job.get("company") or "").lower().strip(),
            (job.get("location") or "").lower().strip(),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_source_registry() -> list[BaseJobSource]:
    """Instantiate all configured job sources."""
    sources: list[BaseJobSource] = []

    try:
        sources.append(AdzunaJobSource())
    except Exception as exc:
        logger.warning("Adzuna source unavailable", extra={"error": str(exc)})

    try:
        sources.append(JSearchJobSource())
    except Exception as exc:
        logger.warning("JSearch source unavailable", extra={"error": str(exc)})

    try:
        sources.append(RemotiveJobSource())
    except Exception as exc:
        logger.warning("Remotive source unavailable", extra={"error": str(exc)})

    try:
        sources.append(RemoteOKJobSource())
    except Exception as exc:
        logger.warning("RemoteOK source unavailable", extra={"error": str(exc)})

    try:
        sources.append(USAJobsSource())
    except Exception as exc:
        logger.warning("USAJobs source unavailable", extra={"error": str(exc)})

    return sources


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------


class JobAggregator:
    """
    Coordinates job fetching, deduplication, and database persistence.

    Usage::

        aggregator = JobAggregator(db_session)
        stats = await aggregator.run(query="python developer", location="remote")
    """

    def __init__(
        self,
        db: AsyncSession,
        sources: Optional[list[BaseJobSource]] = None,
    ) -> None:
        self.db = db
        self.sources = sources if sources is not None else _build_source_registry()

    async def _fetch_from_source(
        self,
        source: BaseJobSource,
        query: str,
        location: Optional[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Safely fetch-and-normalise from one source; return [] on failure."""
        try:
            return await source.fetch_and_normalize(query, location, limit)
        except Exception as exc:
            logger.error(
                "Source fetch/normalise error",
                extra={"source": source.source_name, "error": str(exc)},
            )
            return []

    async def _fetch_all(
        self,
        query: str,
        location: Optional[str],
        limit_per_source: int,
    ) -> list[dict[str, Any]]:
        """Fetch from all sources concurrently."""
        tasks = [
            self._fetch_from_source(source, query, location, limit_per_source)
            for source in self.sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        combined: list[dict[str, Any]] = []
        for batch in results:
            combined.extend(batch)
        return combined

    def _deduplicate(
        self, jobs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove duplicate job postings, keeping the first occurrence."""
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for job in jobs:
            key = _dedup_key(job)
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique

    async def _get_existing_external_ids(
        self, source_ids: list[tuple[str, str]]
    ) -> set[tuple[str, str]]:
        """
        Return the set of (external_id, source) pairs already in the database
        to avoid re-inserting duplicates.
        """
        if not source_ids:
            return set()

        result = await self.db.execute(
            select(Job.external_id, Job.source).where(
                Job.source.in_({s for _, s in source_ids}),
                Job.external_id.in_({eid for eid, _ in source_ids}),
            )
        )
        return {(row.external_id, row.source) for row in result.all()}

    async def _persist_jobs(self, jobs: list[dict[str, Any]]) -> int:
        """
        Insert new jobs into the database.

        Returns the number of new rows inserted.
        """
        if not jobs:
            return 0

        source_id_pairs = [
            (j.get("external_id"), j.get("source"))
            for j in jobs
            if j.get("external_id") and j.get("source")
        ]
        existing = await self._get_existing_external_ids(source_id_pairs)

        new_jobs: list[Job] = []
        for job_data in jobs:
            key = (job_data.get("external_id"), job_data.get("source"))
            if key in existing:
                continue

            metadata = job_data.pop("metadata", None)
            new_job = Job(
                external_id=job_data.get("external_id"),
                source=job_data.get("source", "unknown"),
                title=job_data.get("title", "Untitled"),
                company=job_data.get("company", "Unknown"),
                location=job_data.get("location"),
                description=job_data.get("description"),
                requirements=job_data.get("requirements"),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                job_type=job_data.get("job_type"),
                remote=bool(job_data.get("remote", False)),
                url=job_data.get("url"),
                posted_at=job_data.get("posted_at"),
                metadata_=metadata,
            )
            new_jobs.append(new_job)

        if new_jobs:
            self.db.add_all(new_jobs)
            await self.db.commit()

        return len(new_jobs)

    async def run(
        self,
        query: str = "software engineer",
        location: Optional[str] = None,
        limit_per_source: int = 25,
    ) -> dict[str, Any]:
        """
        Run the full aggregation pipeline.

        1. Fetch from all sources concurrently.
        2. Deduplicate by title+company+location hash.
        3. Filter out already-existing rows.
        4. Persist new jobs.

        Returns a stats dict.
        """
        logger.info(
            "Job aggregation started",
            extra={
                "query": query,
                "location": location,
                "sources": len(self.sources),
            },
        )

        raw_jobs = await self._fetch_all(query, location, limit_per_source)
        total_fetched = len(raw_jobs)

        unique_jobs = self._deduplicate(raw_jobs)
        total_unique = len(unique_jobs)

        new_count = await self._persist_jobs(unique_jobs)

        stats = {
            "total_fetched": total_fetched,
            "total_unique": total_unique,
            "total_saved": new_count,
            "duplicates_skipped": total_unique - new_count,
            "sources_used": len(self.sources),
        }
        logger.info("Job aggregation complete", extra=stats)
        return stats
