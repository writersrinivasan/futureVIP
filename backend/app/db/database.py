"""Async SQLAlchemy engine, session factory, and database dependency."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Convert a sync postgres URL to an async one (asyncpg driver)
# ---------------------------------------------------------------------------
def _build_async_url(url: str) -> str:
    """Ensure the DATABASE_URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


ASYNC_DATABASE_URL = _build_async_url(settings.DATABASE_URL)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "application_name": "futurevip-backend",
        }
    },
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    ``AsyncAttrs`` provides awaitable attribute access so lazy-loaded
    relationships can be awaited inside async contexts.
    """

    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """
    Yield an async database session for the duration of a request.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


async def ping_database() -> bool:
    """Return True when the database is reachable, False otherwise."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health-check failed", extra={"error": str(exc)})
        return False


async def create_tables() -> None:
    """Create all tables that are not yet present (development helper)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified")
