"""FastAPI dependency functions for authentication, authorization, and pagination."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.database import get_db
from app.db.models import User

logger = get_logger(__name__)

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class PaginationParams:
    """Reusable pagination dependency."""

    def __init__(
        self,
        skip: int = Query(default=0, ge=0, description="Number of records to skip"),
        limit: int = Query(
            default=20, ge=1, le=100, description="Maximum records to return"
        ),
    ) -> None:
        self.skip = skip
        self.limit = limit


def get_pagination(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
    """Return validated pagination parameters."""
    p = PaginationParams.__new__(PaginationParams)
    p.skip = skip
    p.limit = limit
    return p


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Decode the bearer JWT and return the corresponding User row.

    Raises HTTP 401 for missing/invalid tokens and HTTP 404 when the user
    no longer exists in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Reject refresh tokens used as access tokens
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cannot be used as an access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        uid = UUID(user_id)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user has an active account."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return current_user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Ensure the authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Convenient type aliases for use in endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
