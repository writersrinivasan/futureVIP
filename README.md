# FUTURE VIP — Agentic AI Career Intelligence Platform

> **Transform your career with AI that thinks, plans, and acts for you.**

FUTURE VIP is a full-stack SaaS platform that acts as a personal career agent — it analyzes your resume, finds the best-fit jobs from across the internet, scores each match with detailed AI reasoning, generates a personalized career roadmap, and coaches you through interview preparation. All autonomously.

---

## Architecture Overview

```
                          ┌─────────────────────────────────────────────┐
                          │                 Users (Browser)              │
                          └──────────────────────┬──────────────────────┘
                                                 │ HTTPS / WSS
                          ┌──────────────────────▼──────────────────────┐
                          │             Nginx (Reverse Proxy)            │
                          │  Rate Limiting · Gzip · SSL/TLS Termination  │
                          └──────────┬──────────────────────┬───────────┘
                                     │ /api/*               │ /*
              ┌──────────────────────▼──────┐  ┌───────────▼────────────┐
              │    FastAPI Backend (Python)  │  │  React SPA (Vite/TS)   │
              │  REST API · WebSocket · Auth │  │  Tailwind · shadcn/ui  │
              └─────────────┬───────────────┘  └────────────────────────┘
                            │
          ┌─────────────────┼────────────────────────────────┐
          │                 │                                │
 ┌────────▼───────┐ ┌──────▼──────┐ ┌──────────────────────▼──────┐
 │  PostgreSQL 16 │ │  Redis 7    │ │       ChromaDB               │
 │  Primary DB    │ │  Cache +    │ │  Vector Store                │
 │  Audit Logs    │ │  Celery     │ │  Resume Embeddings           │
 │  Full-Text     │ │  Broker     │ │  Job Embeddings              │
 └────────────────┘ └──────┬──────┘ │  Semantic Search            │
                           │        └──────────────────────────────┘
          ┌────────────────┼───────────────────┐
          │                │                   │
 ┌────────▼──────┐ ┌───────▼───────┐ ┌────────▼──────────┐
 │ Celery Worker │ │ Celery Beat   │ │ Flower Dashboard  │
 │ AI Tasks      │ │ Scheduler     │ │ Task Monitoring   │
 │ Job Scraping  │ │ Weekly Digest │ │ :5555             │
 │ Notifications │ │ Job Refresh   │ └───────────────────┘
 └───────────────┘ └───────────────┘
          │
 ┌────────▼──────────────────────────────────────────────┐
 │              External AI & Job APIs                    │
 │  OpenAI GPT-4o · text-embedding-3-large               │
 │  Adzuna · JSearch · USAJobs · LinkedIn                 │
 └───────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer            | Technology                                           |
|------------------|------------------------------------------------------|
| **Frontend**     | React 18 · TypeScript · Vite · Tailwind CSS          |
| **Backend**      | Python 3.11 · FastAPI · SQLAlchemy 2 (async)         |
| **Database**     | PostgreSQL 16 · Alembic migrations · Full-text search|
| **Cache/Queue**  | Redis 7 · Celery · Celery Beat                       |
| **Vector Store** | ChromaDB · OpenAI text-embedding-3-large             |
| **AI**           | OpenAI GPT-4o · LangChain · Custom agent framework   |
| **Containers**   | Docker · Docker Compose · Nginx                      |
| **CI/CD**        | GitHub Actions · GHCR · Railway / Vercel             |

---

## Quick Start (Docker)

### Prerequisites

- Docker 24+ with Docker Compose plugin
- Node.js 20+ (for local frontend dev only)
- Python 3.11+ (for local backend dev only)
- 4 GB RAM available for Docker

### 1. Clone the repository

```bash
git clone https://github.com/your-org/futurevip.git
cd futurevip
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and fill in:
#   OPENAI_API_KEY=sk-...
#   ADZUNA_APP_ID=...
#   ADZUNA_API_KEY=...
```

### 3. Run full setup

```bash
# One-command setup: starts all services, runs migrations, seeds demo data
./scripts/setup.sh
```

Or using Make:

```bash
make setup
```

### 4. Access the platform

| Service       | URL                          |
|---------------|------------------------------|
| Frontend      | http://localhost:3000        |
| Backend API   | http://localhost:8000        |
| API Docs      | http://localhost:8000/docs   |
| Flower        | http://localhost:5555        |
| ChromaDB      | http://localhost:8001        |

**Demo accounts:**

| Role  | Email                  | Password               |
|-------|------------------------|------------------------|
| Admin | admin@futurevip.ai     | FutureVIP@Admin2025!   |
| User  | demo@futurevip.ai      | DemoUser@2025!         |

---

## Manual Setup (Development)

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy and configure .env
cp ../.env.example .env
# Edit .env with your API keys

# Start infrastructure only
docker compose up -d postgres redis chromadb

# Run migrations
alembic upgrade head

# Seed database
psql -U futurevip -d future_vip -f ../database/002_seed.sql

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create frontend env
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
```

### Celery Workers

```bash
cd backend

# Worker (in one terminal)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# Beat scheduler (in another terminal)
celery -A app.tasks.celery_app beat --loglevel=info

# Flower monitor (optional)
celery -A app.tasks.celery_app flower --port=5555
```

---

## Environment Variables

### Core Required Variables

| Variable             | Description                                | Example                                      |
|---------------------|--------------------------------------------|----------------------------------------------|
| `DATABASE_URL`      | PostgreSQL async connection URL            | `postgresql+asyncpg://user:pass@host/db`     |
| `REDIS_URL`         | Redis connection URL                       | `redis://redis:6379/0`                       |
| `SECRET_KEY`        | JWT signing key (generate with openssl)    | `openssl rand -hex 32`                       |
| `OPENAI_API_KEY`    | OpenAI API key for AI features             | `sk-...`                                     |
| `ADZUNA_APP_ID`     | Adzuna job board app ID                    | `abc123`                                     |
| `ADZUNA_API_KEY`    | Adzuna job board API key                   | `def456`                                     |

### Optional Variables

| Variable              | Description                               | Default                |
|----------------------|-------------------------------------------|------------------------|
| `ENVIRONMENT`        | `development`, `test`, `production`        | `development`          |
| `DEBUG`              | Enable debug mode                          | `true`                 |
| `ALLOWED_ORIGINS`    | Comma-separated CORS origins               | `http://localhost:3000`|
| `JSEARCH_API_KEY`    | JSearch (RapidAPI) key                    | —                      |
| `USAJOBS_API_KEY`    | USAJobs.gov API key                       | —                      |
| `SENTRY_DSN`         | Sentry error tracking URL                 | —                      |
| `SMTP_HOST`          | Email SMTP host                            | —                      |
| `BACKUP_S3_BUCKET`   | S3 bucket for database backups            | —                      |

See `.env.example` for the full list with descriptions.

---

## Available Make Commands

```
make setup          Full environment setup
make dev            Start all services
make stop           Stop all services
make restart        Restart all services
make build          Build Docker images
make logs           Tail all service logs
make logs-backend   Tail backend logs only
make test           Run all tests
make test-backend   Run backend pytest suite
make test-frontend  Run frontend tests
make lint           Run linters (ruff + ESLint)
make format         Auto-format code
make type-check     Run mypy + tsc
make migrate        Run Alembic migrations
make seed           Seed database with demo data
make backup         Create database backup
make backup-s3      Backup and upload to S3
make health         Check all service health
make shell-backend  Exec bash into backend container
make shell-postgres Exec psql into postgres
make clean          DANGER: Remove all containers + volumes
make reset-dev      DANGER: Full dev environment reset
```

---

## Project Structure

```
FutureVIP/
├── .github/
│   └── workflows/
│       ├── ci.yml           # CI: test, lint, build
│       └── deploy.yml       # CD: push images, deploy
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route handlers
│   │   ├── agents/          # AI agent implementations
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # SQLAlchemy models + migrations
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic layer
│   │   └── tasks/           # Celery tasks
│   ├── tests/               # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/          # Zustand state management
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── database/
│   ├── 001_initial.sql      # Full schema (idempotent)
│   ├── 002_seed.sql         # Demo/dev data
│   └── alembic.ini          # Alembic config
├── docker/
│   ├── nginx.conf           # Nginx production config
│   └── Dockerfile.nginx     # Nginx image
├── scripts/
│   ├── setup.sh             # Full environment setup
│   ├── migrate.sh           # Run Alembic migrations
│   ├── seed.sh              # Seed database
│   ├── backup.sh            # PostgreSQL backup
│   ├── health_check.sh      # Check all services
│   └── reset_dev.sh         # Reset dev environment
├── docker-compose.yml       # Local development
├── docker-compose.prod.yml  # Production overrides
├── Makefile                 # Developer shortcuts
├── .env.example             # Environment variable template
└── .gitignore
```

---

## API Documentation

The API documentation is auto-generated by FastAPI.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key API Endpoints

| Method | Path                            | Description                           |
|--------|---------------------------------|---------------------------------------|
| POST   | `/api/v1/auth/register`         | Register new user                     |
| POST   | `/api/v1/auth/login`            | Login, get JWT                        |
| POST   | `/api/v1/resumes/upload`        | Upload resume (PDF/DOCX)              |
| GET    | `/api/v1/resumes/{id}/analysis` | Get AI resume analysis                |
| GET    | `/api/v1/jobs/`                 | List/search jobs                      |
| GET    | `/api/v1/matches/`              | Get personalized job matches          |
| POST   | `/api/v1/applications/`         | Apply to a job                        |
| GET    | `/api/v1/roadmaps/`             | Get AI career roadmap                 |
| POST   | `/api/v1/interviews/start`      | Start a mock interview session        |
| GET    | `/api/v1/notifications/`        | Get user notifications                |
| GET    | `/health`                       | Service health check                  |

---

## AI Agent System

FUTURE VIP uses a multi-agent architecture where specialized agents handle different career intelligence tasks:

### Resume Analyzer Agent
Parses uploaded resumes, extracts structured data (skills, experience, education), generates ATS scores, and provides improvement recommendations using GPT-4o.

### Job Match Agent
Computes semantic similarity between resume embeddings and job embeddings using ChromaDB + OpenAI embeddings, then uses GPT-4o to generate detailed match explanations with action items.

### Job Aggregator Agent
Runs on a Celery Beat schedule to fetch new job listings from Adzuna, JSearch, and USAJobs APIs, deduplicates, normalizes, and stores them with full-text search indexing.

### Career Roadmap Agent
Analyzes the user's current skills and career goals, identifies skill gaps against target roles, and generates a milestone-based learning roadmap with course and certification recommendations.

### Interview Coach Agent
Generates targeted behavioral and technical interview questions based on the specific job and user background, evaluates responses, and provides structured feedback with improvement areas.

### Notification Agent
Monitors job match scores and application status changes, dispatches real-time in-app notifications and weekly digest emails summarizing career intelligence insights.

---

## Database Schema

The PostgreSQL schema consists of:

| Table                | Description                                          |
|---------------------|------------------------------------------------------|
| `users`             | User accounts, profiles, preferences                 |
| `resumes`           | Uploaded resumes with AI analysis                    |
| `jobs`              | Aggregated job listings from all sources             |
| `job_matches`       | AI-computed match scores (user ↔ job)                |
| `applications`      | Application tracking with full lifecycle             |
| `notifications`     | In-app and email notification records                |
| `user_skills`       | Skill inventory extracted from resumes               |
| `career_roadmaps`   | AI-generated personalized development plans          |
| `interview_sessions`| Mock interview sessions with AI feedback             |
| `audit_logs`        | Immutable audit trail for all significant actions    |

---

## Testing

```bash
# Run all tests
make test

# Backend tests with coverage
make test-backend

# Frontend type check + build
make test-frontend

# Backend tests in watch mode
make test-watch

# Security audit
cd backend && pip-audit
cd frontend && npm audit
```

---

## Deployment

### Production with Docker Compose

```bash
# Start production stack with overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or:
make prod-up
```

### CI/CD with GitHub Actions

1. Push to `main` triggers the CI pipeline (`ci.yml`)
2. On passing CI, the CD pipeline (`deploy.yml`) builds and pushes Docker images to GitHub Container Registry
3. Images are deployed to Railway (backend) and Vercel (frontend)

**Required GitHub Secrets:**

| Secret                    | Description                                |
|--------------------------|--------------------------------------------|
| `RAILWAY_TOKEN`          | Railway API token for backend deployment   |
| `VERCEL_TOKEN`           | Vercel token for frontend deployment       |
| `VERCEL_ORG_ID`          | Vercel organization ID                     |
| `VERCEL_PROJECT_ID`      | Vercel project ID                          |
| `BACKEND_URL`            | Production backend URL (for smoke tests)   |
| `FRONTEND_URL`           | Production frontend URL (for smoke tests)  |
| `VITE_API_URL`           | Backend URL baked into frontend build      |
| `SLACK_WEBHOOK_URL`      | (Optional) Slack deploy notifications      |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with tests
4. Run checks: `make lint && make type-check && make test`
5. Commit following conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
6. Push and open a Pull Request against `develop`

### Code Standards

- **Python**: ruff (linting + formatting), mypy (type checking), pytest (testing)
- **TypeScript**: ESLint + Prettier, tsc strict mode, Vitest (testing)
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
- **Coverage**: Minimum 70% backend coverage enforced in CI

---

## Health Monitoring

```bash
# Check all services
make health

# JSON output (for monitoring tools)
./scripts/health_check.sh --json

# Exit with error if any service is down
./scripts/health_check.sh --exit-on-failure
```

---

## Database Backup & Restore

```bash
# Create local backup
make backup

# Create backup and upload to S3
make backup-s3

# Restore from backup
gunzip backups/futurevip_future_vip_YYYYMMDD_HHMMSS.dump.gz
pg_restore -h localhost -U futurevip -d future_vip --clean --if-exists \
    backups/futurevip_future_vip_YYYYMMDD_HHMMSS.dump
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [ChromaDB](https://www.trychroma.com/) — Open-source vector database
- [OpenAI](https://openai.com/) — GPT-4o and embedding models
- [Adzuna](https://developer.adzuna.com/) — Job listing API

---

*Built with purpose: to make career intelligence accessible to everyone.*
