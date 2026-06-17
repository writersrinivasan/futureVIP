"""Admin-only management endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.v1.deps import AdminUser, DBSession, Pagination
from app.core.logging import get_logger
from app.db.models import Application, AuditLog, Job, Resume, User
from app.db.schemas import (
    AdminStats,
    AuditLogResponse,
    JobResponse,
    MessageResponse,
    PaginatedResponse,
    UserAdminResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)


@router.get(
    "/stats",
    response_model=AdminStats,
    summary="[Admin] Get platform-wide statistics",
)
async def get_platform_stats(
    current_user: AdminUser,
    db: DBSession,
) -> AdminStats:
    """Return aggregate statistics across the entire platform."""
    today = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))  # noqa: E712
    ).scalar_one()
    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar_one()
    total_applications = (await db.execute(select(func.count(Application.id)))).scalar_one()
    total_resumes = (await db.execute(select(func.count(Resume.id)))).scalar_one()

    from app.db.models import JobMatch
    total_matches = (await db.execute(select(func.count(JobMatch.id)))).scalar_one()

    new_users_today = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= today)
        )
    ).scalar_one()
    new_jobs_today = (
        await db.execute(
            select(func.count(Job.id)).where(Job.scraped_at >= today)
        )
    ).scalar_one()

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_jobs=total_jobs,
        total_applications=total_applications,
        total_resumes=total_resumes,
        total_matches=total_matches,
        new_users_today=new_users_today,
        new_jobs_today=new_jobs_today,
    )


@router.get(
    "/users",
    response_model=PaginatedResponse[UserAdminResponse],
    summary="[Admin] List all users",
)
async def list_all_users(
    current_user: AdminUser,
    db: DBSession,
    pagination: Pagination,
    search: Optional[str] = Query(default=None, description="Filter by email or name"),
    is_active: Optional[bool] = Query(default=None),
) -> PaginatedResponse[UserAdminResponse]:
    """Return a paginated list of all platform users."""
    query = select(User)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(User.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    users = result.scalars().all()

    return PaginatedResponse.create(
        items=[UserAdminResponse.model_validate(u) for u in users],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/jobs",
    response_model=PaginatedResponse[JobResponse],
    summary="[Admin] List all jobs",
)
async def list_all_jobs(
    current_user: AdminUser,
    db: DBSession,
    pagination: Pagination,
    source: Optional[str] = Query(default=None),
) -> PaginatedResponse[JobResponse]:
    """Return all jobs in the system, optionally filtered by source."""
    query = select(Job)
    if source:
        query = query.where(Job.source == source)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Job.scraped_at.desc())
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


@router.post(
    "/jobs/refresh",
    response_model=MessageResponse,
    summary="[Admin] Trigger immediate job refresh from all sources",
)
async def refresh_jobs(current_user: AdminUser) -> MessageResponse:
    """Queue a Celery task to immediately re-fetch jobs from all sources."""
    try:
        from app.tasks.job_tasks import discover_jobs_task

        discover_jobs_task.delay()
        logger.info(
            "Admin triggered job refresh",
            extra={"admin_id": str(current_user.id)},
        )
    except Exception as exc:
        logger.error("Failed to queue job refresh", extra={"error": str(exc)})
        return MessageResponse(message="Failed to queue refresh task — Celery unavailable")

    return MessageResponse(
        message="Job refresh task queued. New data will appear within a few minutes."
    )


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="[Admin] View audit log",
)
async def list_audit_logs(
    current_user: AdminUser,
    db: DBSession,
    pagination: Pagination,
    action: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> PaginatedResponse[AuditLogResponse]:
    """Return a paginated, filterable audit log."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    query = select(AuditLog).where(AuditLog.created_at >= since)

    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    logs = result.scalars().all()

    return PaginatedResponse.create(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
