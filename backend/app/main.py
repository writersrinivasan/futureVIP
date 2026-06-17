"""
FUTURE VIP — FastAPI Application Entry Point

Features:
- Async SQLAlchemy with asyncpg
- Redis caching
- ChromaDB vector store
- Celery background tasks
- Structured JSON logging
- Request ID tracing middleware
- CORS, GZip compression
- Global exception handlers
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger, set_request_id, setup_logging

# Initialise structured logging as early as possible
setup_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:
      - Verify database connectivity
      - Initialise Redis client
      - Initialise ChromaDB client

    Shutdown:
      - Gracefully close Redis connection pool
    """
    # ------ Startup ------
    logger.info("FUTURE VIP backend starting", extra={"environment": settings.ENVIRONMENT})

    # Database
    try:
        from app.db.database import ping_database
        db_ok = await ping_database()
        if db_ok:
            logger.info("Database connection verified")
        else:
            logger.error("Database connection FAILED — check DATABASE_URL")
    except Exception as exc:
        logger.error("Database startup check failed", extra={"error": str(exc)})

    # Redis
    try:
        from app.services.cache import cache
        redis_ok = await cache.ping()
        if redis_ok:
            logger.info("Redis connection verified")
        else:
            logger.warning("Redis not available — caching disabled")
    except Exception as exc:
        logger.warning("Redis startup check failed", extra={"error": str(exc)})

    # ChromaDB
    try:
        from app.services.vector_store import init_chroma_client
        init_chroma_client()
        logger.info("ChromaDB client initialised")
    except Exception as exc:
        logger.warning("ChromaDB startup check failed", extra={"error": str(exc)})

    logger.info("FUTURE VIP backend ready to serve requests")

    yield  # ----- Running -----

    # ------ Shutdown ------
    logger.info("FUTURE VIP backend shutting down")
    try:
        from app.services.cache import cache
        await cache.close()
        logger.info("Redis connection closed")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------


def create_application() -> FastAPI:
    app = FastAPI(
        title="FUTURE VIP — Career Intelligence Platform",
        description=(
            "Agentic AI Career Intelligence SaaS: resume analysis, "
            "semantic job matching, career roadmapping, and mock interviews."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ---- Middleware ----

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression for responses larger than 1 KB
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ---- Request ID + Access log middleware ----

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """
        Attach a unique request ID to every request and emit a structured
        access log line with duration.  Also propagates the caller's OpenAI
        key (if supplied) into a contextvar so agents can use it.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # BYOK: let users supply their own OpenAI key via header
        from app.core.context import user_openai_key
        caller_key = request.headers.get("X-OpenAI-Api-Key")
        if caller_key:
            user_openai_key.set(caller_key)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
                "client_ip": (
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                    or (request.client.host if request.client else "unknown")
                ),
            },
        )
        return response

    # ---- Routers ----

    from app.api.v1.router import api_router
    app.include_router(api_router, prefix="/api/v1")

    # ---- Root endpoints ----

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root():
        return {
            "name": "FUTURE VIP",
            "description": "By Unemployed, For Unemployed",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def liveness_probe():
        """Lightweight liveness probe — does not check external services."""
        return {"status": "alive", "service": "futurevip-backend", "version": "1.0.0"}

    # ---- Exception handlers ----

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": " -> ".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg"),
                "type": error.get("type"),
            }
            for error in exc.errors()
        ]
        logger.warning(
            "Request validation error",
            extra={"path": request.url.path, "errors": errors},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": errors},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        logger.info(
            "HTTP exception",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": (
                    "An unexpected internal error occurred. "
                    "Our team has been notified."
                )
            },
        )

    return app


app = create_application()
