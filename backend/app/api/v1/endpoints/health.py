"""Health check endpoints for liveness and readiness probes."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.db.schemas import HealthResponse, ServiceStatus

router = APIRouter(prefix="/health", tags=["Health"])
logger = get_logger(__name__)


async def _check_database() -> ServiceStatus:
    """Ping the database and return its status."""
    start = time.monotonic()
    try:
        from app.db.database import ping_database

        ok = await ping_database()
        latency_ms = (time.monotonic() - start) * 1000
        return ServiceStatus(
            status="ok" if ok else "down",
            latency_ms=round(latency_ms, 2),
        )
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        logger.warning("DB health check failed", extra={"error": str(exc)})
        return ServiceStatus(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=str(exc),
        )


async def _check_redis() -> ServiceStatus:
    """Ping Redis and return its status."""
    start = time.monotonic()
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        latency_ms = (time.monotonic() - start) * 1000
        return ServiceStatus(status="ok", latency_ms=round(latency_ms, 2))
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        logger.warning("Redis health check failed", extra={"error": str(exc)})
        return ServiceStatus(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=str(exc),
        )


async def _check_chromadb() -> ServiceStatus:
    """Verify ChromaDB is accessible and return its status."""
    start = time.monotonic()
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        client.heartbeat()
        latency_ms = (time.monotonic() - start) * 1000
        return ServiceStatus(status="ok", latency_ms=round(latency_ms, 2))
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        logger.warning("ChromaDB health check failed", extra={"error": str(exc)})
        return ServiceStatus(
            status="degraded",
            latency_ms=round(latency_ms, 2),
            detail=str(exc),
        )


@router.get(
    "",
    response_model=HealthResponse,
    summary="Full health check — includes all service statuses",
)
async def health_check() -> HealthResponse:
    """
    Return the health status of all platform dependencies.

    The HTTP response code is 200 when all services are healthy, and 503 when
    any critical service (database) is unavailable.
    """
    db_status = await _check_database()
    redis_status = await _check_redis()
    chroma_status = await _check_chromadb()

    all_statuses = [db_status, redis_status, chroma_status]
    if any(s.status == "down" for s in all_statuses):
        overall = "unhealthy"
    elif any(s.status == "degraded" for s in all_statuses):
        overall = "degraded"
    else:
        overall = "healthy"

    response = HealthResponse(
        status=overall,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        services={
            "database": db_status,
            "redis": redis_status,
            "chromadb": chroma_status,
        },
        timestamp=datetime.now(tz=timezone.utc),
    )

    http_status = (
        status.HTTP_200_OK
        if overall in ("healthy", "degraded")
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=http_status,
    )


@router.get(
    "/ready",
    summary="Readiness probe — returns 200 only when ready to serve traffic",
)
async def readiness_check() -> JSONResponse:
    """
    Kubernetes-style readiness probe.

    Returns 200 OK when the database connection is healthy (minimum requirement
    to handle requests). Returns 503 otherwise.
    """
    db_status = await _check_database()
    if db_status.status == "ok":
        return JSONResponse(
            content={"status": "ready", "timestamp": datetime.now(tz=timezone.utc).isoformat()},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={
            "status": "not ready",
            "reason": "database unavailable",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
