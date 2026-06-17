"""Authentication endpoints: register, login, refresh, logout, me."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import AuditLog, User
from app.db.schemas import (
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _create_audit_log(
    db: AsyncSession,
    action: str,
    user_id=None,
    resource_type: str = "auth",
    resource_id: str = None,
    details: dict = None,
    ip_address: str = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(log)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_data: UserCreate,
    request: Request,
    db: DBSession,
) -> UserResponse:
    """Create a new user account."""
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_admin=False,
    )
    db.add(new_user)
    await db.flush()  # get the generated id before audit log

    await _create_audit_log(
        db,
        action="user_register",
        user_id=new_user.id,
        resource_id=str(new_user.id),
        details={"email": new_user.email},
        ip_address=_client_ip(request),
    )

    await db.commit()
    await db.refresh(new_user)
    logger.info("New user registered", extra={"user_id": str(new_user.id)})
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and obtain JWT tokens",
)
async def login(
    credentials: UserLogin,
    request: Request,
    db: DBSession,
) -> TokenResponse:
    """Authenticate with email and password; returns access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last_login
    user.last_login = datetime.now(tz=timezone.utc)

    await _create_audit_log(
        db,
        action="user_login",
        user_id=user.id,
        resource_id=str(user.id),
        ip_address=_client_ip(request),
    )

    await db.commit()
    logger.info("User logged in", extra={"user_id": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Obtain a new access token using a refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: DBSession,
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise invalid_exc

    user_id = payload.get("sub")
    if not user_id:
        raise invalid_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid_exc

    token_data = {"sub": str(user.id), "email": user.email}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out (client-side token invalidation)",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    request: Request,
    db: DBSession,
) -> MessageResponse:
    """
    Log out the current user.

    Because JWT tokens are stateless, true server-side invalidation requires a
    token deny-list (Redis). This endpoint records the logout audit event and
    instructs the client to discard its tokens.
    """
    if credentials:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub") if payload else None
        if user_id:
            await _create_audit_log(
                db,
                action="user_logout",
                user_id=user_id,
                resource_id=user_id,
                ip_address=_client_ip(request),
            )
            await db.commit()

    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def get_me(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DBSession,
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_validate(user)
