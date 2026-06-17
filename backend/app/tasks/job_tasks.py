"""
Celery tasks for job discovery, semantic matching, and notifications.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import delete, select

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine in a synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Job discovery
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.discover_jobs_task",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=300,
    time_limit=600,
)
def discover_jobs_task(
    self: Task,
    query: str = "software engineer",
    location: Optional[str] = None,
    limit_per_source: int = 25,
) -> dict[str, Any]:
    """
    Fetch new job listings from all integrated sources and persist them.

    This task is scheduled via Celery Beat every 6 hours and can also be
    triggered on-demand from the admin endpoint.
    """
    logger.info(
        "discover_jobs_task started",
        extra={"query": query, "location": location},
    )

    async def _run() -> dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.services.job_aggregator import JobAggregator

        async with AsyncSessionLocal() as db:
            aggregator = JobAggregator(db)
            return await aggregator.run(
                query=query,
                location=location,
                limit_per_source=limit_per_source,
            )

    try:
        stats = _run_async(_run())
        logger.info("discover_jobs_task complete", extra=stats)
        return stats
    except SoftTimeLimitExceeded:
        logger.warning("discover_jobs_task: soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error("discover_jobs_task failed", extra={"error": str(exc)})
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.generate_embeddings_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=240,
    time_limit=480,
)
def generate_embeddings_task(
    self: Task,
    resume_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate and upsert embeddings for a resume (or all active resumes when
    ``resume_id`` is None — used by the nightly refresh beat task).
    """
    logger.info("generate_embeddings_task started", extra={"resume_id": resume_id})

    async def _run() -> dict[str, Any]:
        from openai import AsyncOpenAI

        from app.db.database import AsyncSessionLocal
        from app.db.models import Resume
        from app.services.vector_store import upsert_resume_embeddings

        openai_client = AsyncOpenAI()
        processed = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            if resume_id:
                result = await db.execute(
                    select(Resume).where(Resume.id == resume_id, Resume.is_active == True)  # noqa: E712
                )
                resumes = [r for r in [result.scalar_one_or_none()] if r]
            else:
                result = await db.execute(
                    select(Resume).where(
                        Resume.is_active == True,  # noqa: E712
                        Resume.content_text.isnot(None),
                    )
                )
                resumes = list(result.scalars().all())

            for resume in resumes:
                if not resume.content_text:
                    continue
                try:
                    # Chunk the resume text (simple fixed-size chunking)
                    text = resume.content_text
                    chunk_size = 500
                    chunks = [
                        text[i: i + chunk_size]
                        for i in range(0, len(text), chunk_size)
                    ]
                    chunks = [c for c in chunks if c.strip()]

                    if not chunks:
                        continue

                    # Batch embed all chunks
                    response = await openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=chunks,
                    )
                    embeddings = [item.embedding for item in response.data]

                    upsert_resume_embeddings(
                        resume_id=str(resume.id),
                        chunks=chunks,
                        embeddings=embeddings,
                        metadata={"user_id": str(resume.user_id)},
                    )
                    processed += 1
                except Exception as exc:
                    logger.error(
                        "Embedding failed for resume",
                        extra={"resume_id": str(resume.id), "error": str(exc)},
                    )
                    errors += 1

        return {"processed": processed, "errors": errors}

    try:
        result = _run_async(_run())
        logger.info("generate_embeddings_task complete", extra=result)
        return result
    except SoftTimeLimitExceeded:
        logger.warning("generate_embeddings_task: soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error("generate_embeddings_task failed", extra={"error": str(exc)})
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Semantic job matching
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.match_jobs_for_user_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=180,
    time_limit=360,
)
def match_jobs_for_user_task(self: Task, user_id: str) -> dict[str, Any]:
    """
    Run semantic job matching for a specific user.

    1. Load the user's most recent active resume embedding.
    2. Query ChromaDB for the top-N matching job embeddings.
    3. Upsert JobMatch rows in the database.
    4. Send a notification if new matches are found.
    """
    logger.info("match_jobs_for_user_task started", extra={"user_id": user_id})

    async def _run() -> dict[str, Any]:
        from openai import AsyncOpenAI

        from app.db.database import AsyncSessionLocal
        from app.db.models import Job, JobMatch, Resume
        from app.services.vector_store import search_matching_jobs

        openai_client = AsyncOpenAI()

        async with AsyncSessionLocal() as db:
            # Load active resume with text
            result = await db.execute(
                select(Resume).where(
                    Resume.user_id == user_id,
                    Resume.is_active == True,  # noqa: E712
                    Resume.content_text.isnot(None),
                ).order_by(Resume.created_at.desc()).limit(1)
            )
            resume = result.scalar_one_or_none()
            if not resume:
                return {"matched": 0, "reason": "no active resume with content"}

            # Generate resume embedding
            embed_response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=(resume.content_text or "")[:8000],
            )
            resume_vector = embed_response.data[0].embedding

            # Semantic search in ChromaDB
            similar_jobs = search_matching_jobs(
                resume_embedding=resume_vector,
                top_k=20,
            )

            if not similar_jobs:
                return {"matched": 0, "reason": "no job embeddings available"}

            # Upsert JobMatch rows
            new_matches = 0
            for job_result in similar_jobs:
                job_id = job_result["job_id"]
                score = job_result["score"]

                # Verify job still exists
                job_check = await db.execute(select(Job).where(Job.id == job_id))
                if not job_check.scalar_one_or_none():
                    continue

                existing = await db.execute(
                    select(JobMatch).where(
                        JobMatch.user_id == user_id,
                        JobMatch.job_id == job_id,
                        JobMatch.resume_id == resume.id,
                    )
                )
                match_row = existing.scalar_one_or_none()

                if match_row:
                    match_row.match_score = score
                else:
                    new_match = JobMatch(
                        user_id=resume.user_id,
                        job_id=job_id,
                        resume_id=resume.id,
                        match_score=score,
                        reasoning=f"Semantic similarity score: {score:.4f}",
                    )
                    db.add(new_match)
                    new_matches += 1

            await db.commit()

            if new_matches > 0:
                send_notification_task.delay(
                    user_id=user_id,
                    notification_type="job_match",
                    title="New Job Matches Found!",
                    message=f"We found {new_matches} new job matches for your profile.",
                    data={"new_matches": new_matches},
                )

            return {"matched": len(similar_jobs), "new_matches": new_matches}

    try:
        result = _run_async(_run())
        logger.info("match_jobs_for_user_task complete", extra=result)
        return result
    except SoftTimeLimitExceeded:
        logger.warning("match_jobs_for_user_task: soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error(
            "match_jobs_for_user_task failed",
            extra={"user_id": user_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.send_notification_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=30,
    time_limit=60,
)
def send_notification_task(
    self: Task,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Persist an in-app notification row for the given user."""

    async def _run() -> dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Notification, NotificationType

        try:
            n_type = NotificationType(notification_type)
        except ValueError:
            n_type = NotificationType.SYSTEM

        async with AsyncSessionLocal() as db:
            notification = Notification(
                user_id=user_id,
                type=n_type,
                title=title,
                message=message,
                data=data or {},
            )
            db.add(notification)
            await db.commit()

        return {"status": "sent", "user_id": user_id, "type": notification_type}

    try:
        result = _run_async(_run())
        return result
    except Exception as exc:
        logger.error(
            "send_notification_task failed",
            extra={"user_id": user_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.job_tasks.cleanup_old_jobs_task",
    bind=True,
    max_retries=2,
    soft_time_limit=120,
    time_limit=240,
)
def cleanup_old_jobs_task(self: Task, days: int = 30) -> dict[str, Any]:
    """
    Remove job postings (and their embeddings) that are older than *days* days.
    """
    logger.info("cleanup_old_jobs_task started", extra={"days": days})

    async def _run() -> dict[str, Any]:
        from app.db.database import AsyncSessionLocal
        from app.db.models import Job
        from app.services.vector_store import delete_job_embeddings

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job.id).where(Job.scraped_at < cutoff)
            )
            old_ids = [str(row.id) for row in result.all()]

            if not old_ids:
                return {"deleted": 0}

            # Remove embeddings first
            for job_id in old_ids:
                try:
                    delete_job_embeddings(job_id)
                except Exception as exc:
                    logger.warning(
                        "Could not delete job embedding",
                        extra={"job_id": job_id, "error": str(exc)},
                    )

            # Bulk-delete from DB
            await db.execute(
                delete(Job).where(Job.scraped_at < cutoff)
            )
            await db.commit()

        logger.info(
            "cleanup_old_jobs_task complete",
            extra={"deleted": len(old_ids), "cutoff": cutoff.isoformat()},
        )
        return {"deleted": len(old_ids)}

    try:
        result = _run_async(_run())
        return result
    except SoftTimeLimitExceeded:
        logger.warning("cleanup_old_jobs_task: soft time limit exceeded")
        raise
    except Exception as exc:
        logger.error("cleanup_old_jobs_task failed", extra={"error": str(exc)})
        raise self.retry(exc=exc)
