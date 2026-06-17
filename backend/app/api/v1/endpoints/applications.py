"""Job application tracking endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import CurrentUser, DBSession, Pagination
from app.core.logging import get_logger
from app.db.models import Application, ApplicationStatus, Job
from app.db.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStats,
    ApplicationUpdate,
    MessageResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/applications", tags=["Applications"])
logger = get_logger(__name__)


async def _get_application_or_404(
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    db,
) -> Application:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job))
        .where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return app


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job application record",
)
async def create_application(
    application_data: ApplicationCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ApplicationResponse:
    """Save or track a new job application."""
    # Verify job exists
    job_result = await db.execute(
        select(Job).where(Job.id == application_data.job_id)
    )
    if job_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check for duplicate
    existing = await db.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == application_data.job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an application for this job",
        )

    application = Application(
        user_id=current_user.id,
        job_id=application_data.job_id,
        status=application_data.status,
        notes=application_data.notes,
        follow_up_date=application_data.follow_up_date,
        applied_at=(
            datetime.now(tz=timezone.utc)
            if application_data.status == ApplicationStatus.APPLIED
            else None
        ),
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.id == application.id)
    )
    application = result.scalar_one()

    logger.info(
        "Application created",
        extra={
            "user_id": str(current_user.id),
            "application_id": str(application.id),
            "job_id": str(application.job_id),
        },
    )
    return ApplicationResponse.model_validate(application)


@router.get(
    "/",
    response_model=PaginatedResponse[ApplicationResponse],
    summary="List current user's applications",
)
async def list_applications(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    status_filter: Optional[ApplicationStatus] = None,
) -> PaginatedResponse[ApplicationResponse]:
    """Return a paginated list of the current user's applications."""
    query = (
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.user_id == current_user.id)
    )
    if status_filter:
        query = query.where(Application.status == status_filter)

    count_q = select(func.count()).select_from(
        select(Application).where(Application.user_id == current_user.id).subquery()
    )
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Application.updated_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    applications = result.scalars().all()

    return PaginatedResponse.create(
        items=[ApplicationResponse.model_validate(a) for a in applications],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/stats",
    response_model=ApplicationStats,
    summary="Get application funnel statistics",
)
async def get_application_stats(
    current_user: CurrentUser,
    db: DBSession,
) -> ApplicationStats:
    """Return application counts broken down by status for the current user."""
    result = await db.execute(
        select(Application.status, func.count(Application.id).label("count"))
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )
    rows = result.all()
    counts = {row.status: row.count for row in rows}

    total = sum(counts.values())
    applied = counts.get(ApplicationStatus.APPLIED, 0)
    interview = counts.get(ApplicationStatus.INTERVIEW, 0)
    offer = counts.get(ApplicationStatus.OFFER, 0)

    return ApplicationStats(
        total=total,
        saved=counts.get(ApplicationStatus.SAVED, 0),
        applied=applied,
        screening=counts.get(ApplicationStatus.SCREENING, 0),
        interview=interview,
        offer=offer,
        rejected=counts.get(ApplicationStatus.REJECTED, 0),
        withdrawn=counts.get(ApplicationStatus.WITHDRAWN, 0),
        conversion_rate=round((offer / applied * 100) if applied > 0 else 0.0, 1),
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get a specific application",
)
async def get_application(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ApplicationResponse:
    """Return details of a specific application."""
    application = await _get_application_or_404(application_id, current_user.id, db)
    return ApplicationResponse.model_validate(application)


@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application",
)
async def update_application(
    application_id: uuid.UUID,
    updates: ApplicationUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> ApplicationResponse:
    """Update status, notes, or follow-up date on an application."""
    application = await _get_application_or_404(application_id, current_user.id, db)

    if updates.status is not None:
        application.status = updates.status
        if updates.status == ApplicationStatus.APPLIED and application.applied_at is None:
            application.applied_at = datetime.now(tz=timezone.utc)

    if updates.notes is not None:
        application.notes = updates.notes

    if updates.follow_up_date is not None:
        application.follow_up_date = updates.follow_up_date

    if updates.applied_at is not None:
        application.applied_at = updates.applied_at

    await db.commit()
    await db.refresh(application)

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.id == application.id)
    )
    application = result.scalar_one()

    return ApplicationResponse.model_validate(application)


@router.delete(
    "/{application_id}",
    response_model=MessageResponse,
    summary="Delete an application record",
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Remove a job application record."""
    application = await _get_application_or_404(application_id, current_user.id, db)
    await db.delete(application)
    await db.commit()
    return MessageResponse(message="Application deleted successfully")
