"""User management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, Pagination, get_pagination
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import (
    MessageResponse,
    PaginatedResponse,
    UserAdminResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger(__name__)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    updates: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserResponse:
    """Update the authenticated user's profile fields."""
    if updates.email and updates.email != current_user.email:
        existing = await db.execute(
            select(User).where(User.email == updates.email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another account",
            )
        current_user.email = updates.email

    if updates.full_name is not None:
        current_user.full_name = updates.full_name

    if updates.password is not None:
        current_user.hashed_password = hash_password(updates.password)

    await db.commit()
    await db.refresh(current_user)
    logger.info("User profile updated", extra={"user_id": str(current_user.id)})
    return UserResponse.model_validate(current_user)


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete current user account",
)
async def delete_my_account(
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Permanently delete the authenticated user's account."""
    await db.delete(current_user)
    await db.commit()
    logger.info("User account deleted", extra={"user_id": str(current_user.id)})
    return MessageResponse(message="Account deleted successfully")


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedResponse[UserAdminResponse],
    summary="[Admin] List all users",
)
async def list_users(
    current_user: AdminUser,
    db: DBSession,
    pagination: Pagination,
    is_active: bool | None = Query(default=None),
    is_admin: bool | None = Query(default=None),
) -> PaginatedResponse[UserAdminResponse]:
    """Return a paginated list of all users (admin only)."""
    query = select(User)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if is_admin is not None:
        query = query.where(User.is_admin == is_admin)

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
    "/{user_id}",
    response_model=UserAdminResponse,
    summary="[Admin] Get user by ID",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: AdminUser,
    db: DBSession,
) -> UserAdminResponse:
    """Return a specific user's details (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserAdminResponse.model_validate(user)
