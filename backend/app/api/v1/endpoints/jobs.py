"""Job discovery and matching endpoints."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, DBSession, Pagination
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models import Job, JobMatch, JobType, Resume
from app.db.schemas import (
    JobDiscoverRequest,
    JobMatchResponse,
    JobResponse,
    JobSearchParams,
    MessageResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = get_logger(__name__)


def _apply_job_filters(query, params: JobSearchParams):
    """Apply search filters to a SQLAlchemy Job query."""
    from sqlalchemy import func

    if params.title:
        query = query.where(Job.title.ilike(f"%{params.title}%"))
    if params.company:
        query = query.where(Job.company.ilike(f"%{params.company}%"))
    if params.location:
        query = query.where(Job.location.ilike(f"%{params.location}%"))
    if params.remote is not None:
        query = query.where(Job.remote == params.remote)
    if params.job_type:
        query = query.where(Job.job_type == params.job_type)
    if params.source:
        query = query.where(Job.source == params.source)
    if params.min_salary is not None:
        query = query.where(
            or_(Job.salary_min >= params.min_salary, Job.salary_max >= params.min_salary)
        )
    if params.max_salary is not None:
        query = query.where(
            or_(Job.salary_max <= params.max_salary, Job.salary_min <= params.max_salary)
        )
    if params.query:
        search_term = f"%{params.query}%"
        query = query.where(
            or_(
                Job.title.ilike(search_term),
                Job.company.ilike(search_term),
                Job.description.ilike(search_term),
            )
        )
    return query


@router.get(
    "/",
    response_model=PaginatedResponse[JobResponse],
    summary="List jobs with optional filters",
)
async def list_jobs(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    title: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    remote: Optional[bool] = Query(default=None),
    job_type: Optional[JobType] = Query(default=None),
    source: Optional[str] = Query(default=None),
    min_salary: Optional[float] = Query(default=None),
    max_salary: Optional[float] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Full-text search"),
) -> PaginatedResponse[JobResponse]:
    """Return a paginated, filterable list of available jobs."""
    from sqlalchemy import func

    params = JobSearchParams(
        query=q,
        title=title,
        company=company,
        location=location,
        remote=remote,
        job_type=job_type,
        source=source,
        min_salary=min_salary,
        max_salary=max_salary,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    base_query = select(Job)
    base_query = _apply_job_filters(base_query, params)

    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        base_query.order_by(Job.scraped_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    jobs = result.scalars().all()

    return PaginatedResponse.create(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/sources",
    response_model=list[dict],
    summary="List available job data sources",
)
async def list_sources(current_user: CurrentUser) -> list[dict]:
    """Return the list of integrated job data sources and their status."""
    return [
        {"name": "adzuna", "display_name": "Adzuna", "active": True},
        {"name": "jsearch", "display_name": "JSearch (RapidAPI)", "active": True},
        {"name": "remotive", "display_name": "Remotive", "active": True},
        {"name": "remoteok", "display_name": "RemoteOK", "active": True},
        {"name": "usajobs", "display_name": "USAJobs", "active": True},
    ]


@router.get(
    "/matches",
    response_model=PaginatedResponse[JobMatchResponse],
    summary="Get semantic job matches for the current user",
)
async def get_job_matches(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    min_score: float = Query(default=0.5, ge=0.0, le=1.0),
) -> PaginatedResponse[JobMatchResponse]:
    """
    Return pre-computed semantic job matches for the authenticated user,
    ordered by match score descending.
    """
    from sqlalchemy import func
    from sqlalchemy.orm import selectinload

    query = (
        select(JobMatch)
        .options(selectinload(JobMatch.job))
        .where(
            JobMatch.user_id == current_user.id,
            JobMatch.match_score >= min_score,
        )
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(JobMatch.match_score.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    matches = result.scalars().all()

    return PaginatedResponse.create(
        items=[JobMatchResponse.model_validate(m) for m in matches],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post(
    "/search",
    response_model=PaginatedResponse[JobResponse],
    summary="Search jobs with a rich query body",
)
async def search_jobs(
    search_params: JobSearchParams,
    current_user: CurrentUser,
    db: DBSession,
) -> PaginatedResponse[JobResponse]:
    """Search jobs using a request body for richer filter combinations."""
    from sqlalchemy import func

    base_query = select(Job)
    base_query = _apply_job_filters(base_query, search_params)

    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        base_query.order_by(Job.scraped_at.desc())
        .offset(search_params.skip)
        .limit(search_params.limit)
    )
    jobs = result.scalars().all()

    return PaginatedResponse.create(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
    )


@router.post(
    "/discover",
    response_model=MessageResponse,
    summary="Trigger immediate job discovery across all sources",
)
async def discover_jobs(
    discover_request: JobDiscoverRequest,
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Queue a one-off job discovery task that fetches new postings from all
    integrated sources and stores them in the database.
    """
    try:
        from app.tasks.job_tasks import discover_jobs_task
        discover_jobs_task.delay()
        logger.info(
            "Job discovery triggered",
            extra={
                "user_id": str(current_user.id),
                "query": discover_request.query,
                "location": discover_request.location,
            },
        )
    except Exception as exc:
        logger.warning("Failed to queue discovery task", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job discovery service temporarily unavailable",
        )

    return MessageResponse(
        message="Job discovery task queued successfully. "
        "New jobs will appear within a few minutes."
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a specific job by ID",
)
async def get_job(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> JobResponse:
    """Return details of a specific job posting."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)
