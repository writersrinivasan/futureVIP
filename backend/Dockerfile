# ── Stage 1: dependency builder ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for psycopg2, pdfplumber, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="FUTURE VIP <team@futurevip.ai>"
LABEL description="FUTURE VIP Backend — Agentic AI Career Intelligence"

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpoppler-cpp0v5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r futurevip && useradd -r -g futurevip futurevip

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=futurevip:futurevip backend/ .

# Create directories for uploads and chroma data
RUN mkdir -p /app/uploads /app/data/chroma && \
    chown -R futurevip:futurevip /app/uploads /app/data/chroma

USER futurevip

# Health check — uses $PORT so Railway's dynamic port is respected
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health" || exit 1

EXPOSE 8000

# $PORT is injected by Railway (and other PaaS); falls back to 8000 locally
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
