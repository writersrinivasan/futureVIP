# =============================================================================
#  FUTURE VIP — Makefile
#  Shortcuts for common development tasks
#  Usage: make <target>
# =============================================================================

.PHONY: help setup dev stop restart logs test test-backend test-frontend \
        migrate seed backup clean build shell-backend shell-frontend \
        shell-postgres health lint format type-check

# ─── Configuration ────────────────────────────────────────────────────────────
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
PROJECT_NAME   := futurevip
BACKEND_CONTAINER  := futurevip_backend
FRONTEND_CONTAINER := futurevip_frontend
POSTGRES_CONTAINER := futurevip_postgres

# Colors
RESET  := \033[0m
BOLD   := \033[1m
GREEN  := \033[32m
BLUE   := \033[34m
YELLOW := \033[33m
RED    := \033[31m

# Default target
.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────
#  HELP
# ─────────────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)FUTURE VIP — Developer Commands$(RESET)"
	@echo ""
	@echo "$(BOLD)Setup & Startup:$(RESET)"
	@grep -E '^(setup|dev|stop|restart|build):.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Database:$(RESET)"
	@grep -E '^(migrate|seed|backup):.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Development:$(RESET)"
	@grep -E '^(logs|test|test-backend|test-frontend|lint|format|type-check|health):.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Shells:$(RESET)"
	@grep -E '^shell-.*:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Cleanup:$(RESET)"
	@grep -E '^clean.*:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─────────────────────────────────────────────────────
#  SETUP & STARTUP
# ─────────────────────────────────────────────────────
setup: ## Run full environment setup (deps check, env files, DB init, seed)
	@echo "$(BOLD)$(BLUE)Running full setup...$(RESET)"
	@chmod +x scripts/*.sh
	@./scripts/setup.sh

dev: ## Start all development services
	@echo "$(BOLD)$(GREEN)Starting all services...$(RESET)"
	@$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)Services started:$(RESET)"
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Backend:    http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo "  Flower:     http://localhost:5555"

infra: ## Start only infrastructure (postgres, redis, chromadb)
	@echo "$(BOLD)Starting infrastructure services...$(RESET)"
	@$(DOCKER_COMPOSE) up -d postgres redis chromadb

stop: ## Stop all services
	@echo "$(BOLD)Stopping all services...$(RESET)"
	@$(DOCKER_COMPOSE) stop

down: ## Stop and remove containers (keeps volumes)
	@echo "$(BOLD)Removing containers...$(RESET)"
	@$(DOCKER_COMPOSE) down --remove-orphans

restart: ## Restart all services
	@echo "$(BOLD)Restarting all services...$(RESET)"
	@$(DOCKER_COMPOSE) restart

restart-backend: ## Restart only the backend container
	@$(DOCKER_COMPOSE) restart backend celery_worker celery_beat

build: ## Build all Docker images
	@echo "$(BOLD)$(BLUE)Building Docker images...$(RESET)"
	@$(DOCKER_COMPOSE) build --parallel

build-backend: ## Build only the backend Docker image
	@$(DOCKER_COMPOSE) build backend

build-frontend: ## Build only the frontend Docker image
	@$(DOCKER_COMPOSE) build frontend

# ─────────────────────────────────────────────────────
#  LOGS
# ─────────────────────────────────────────────────────
logs: ## Tail logs from all services (Ctrl-C to stop)
	@$(DOCKER_COMPOSE) logs -f --tail=100

logs-backend: ## Tail backend logs only
	@$(DOCKER_COMPOSE) logs -f --tail=100 backend

logs-frontend: ## Tail frontend logs only
	@$(DOCKER_COMPOSE) logs -f --tail=100 frontend

logs-worker: ## Tail celery worker logs
	@$(DOCKER_COMPOSE) logs -f --tail=100 celery_worker

logs-db: ## Tail postgres logs
	@$(DOCKER_COMPOSE) logs -f --tail=100 postgres

ps: ## Show status of all containers
	@$(DOCKER_COMPOSE) ps

# ─────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────
migrate: ## Run database migrations (Alembic upgrade head)
	@echo "$(BOLD)$(BLUE)Running database migrations...$(RESET)"
	@chmod +x scripts/migrate.sh
	@./scripts/migrate.sh

migrate-dry: ## Show pending migrations without applying
	@./scripts/migrate.sh --dry-run

seed: ## Seed database with sample data
	@echo "$(BOLD)$(BLUE)Seeding database...$(RESET)"
	@chmod +x scripts/seed.sh
	@./scripts/seed.sh

seed-reset: ## Reset and re-seed database (DESTROYS existing data)
	@echo "$(YELLOW)WARNING: This will delete all data in the database!$(RESET)"
	@./scripts/seed.sh --reset

backup: ## Create a timestamped database backup
	@echo "$(BOLD)$(BLUE)Creating database backup...$(RESET)"
	@chmod +x scripts/backup.sh
	@./scripts/backup.sh

backup-s3: ## Create backup and upload to S3
	@chmod +x scripts/backup.sh
	@./scripts/backup.sh --s3

makemigration: ## Create a new Alembic migration (usage: make makemigration MSG="add users table")
	@$(DOCKER_COMPOSE) exec backend sh -c "cd /app && alembic revision --autogenerate -m '$(MSG)'"

# ─────────────────────────────────────────────────────
#  TESTING
# ─────────────────────────────────────────────────────
test: test-backend test-frontend ## Run all tests (backend + frontend)

test-backend: ## Run backend tests with pytest
	@echo "$(BOLD)$(BLUE)Running backend tests...$(RESET)"
	@$(DOCKER_COMPOSE) exec backend sh -c \
		"cd /app && pytest tests/ -v --cov=app --cov-report=term-missing"

test-backend-ci: ## Run backend tests in CI mode (no docker)
	@echo "$(BOLD)$(BLUE)Running backend tests (local)...$(RESET)"
	@cd backend && python -m pytest tests/ -v --cov=app --cov-report=xml

test-frontend: ## Run frontend tests
	@echo "$(BOLD)$(BLUE)Running frontend tests...$(RESET)"
	@$(DOCKER_COMPOSE) exec frontend sh -c "npm run test --if-present"

test-watch: ## Run backend tests in watch mode
	@$(DOCKER_COMPOSE) exec backend sh -c \
		"cd /app && pytest tests/ -v -f --cov=app"

# ─────────────────────────────────────────────────────
#  CODE QUALITY
# ─────────────────────────────────────────────────────
lint: ## Run all linters (ruff for Python, ESLint for TypeScript)
	@echo "$(BOLD)$(BLUE)Running linters...$(RESET)"
	@$(DOCKER_COMPOSE) exec backend sh -c "cd /app && ruff check app/ tests/"
	@$(DOCKER_COMPOSE) exec frontend sh -c "npm run lint" || true

lint-backend: ## Run Python linter (ruff)
	@$(DOCKER_COMPOSE) exec backend sh -c "cd /app && ruff check app/ tests/ --fix"

format: ## Auto-format code (ruff for Python, prettier for TypeScript)
	@echo "$(BOLD)$(BLUE)Formatting code...$(RESET)"
	@$(DOCKER_COMPOSE) exec backend sh -c "cd /app && ruff format app/ tests/"
	@$(DOCKER_COMPOSE) exec frontend sh -c "npx prettier --write src/" || true

type-check: ## Run type checking (mypy + tsc)
	@echo "$(BOLD)$(BLUE)Running type checks...$(RESET)"
	@$(DOCKER_COMPOSE) exec backend sh -c "cd /app && mypy app/ --ignore-missing-imports" || true
	@$(DOCKER_COMPOSE) exec frontend sh -c "npm run type-check"

health: ## Check health of all services
	@echo "$(BOLD)$(BLUE)Checking service health...$(RESET)"
	@chmod +x scripts/health_check.sh
	@./scripts/health_check.sh

# ─────────────────────────────────────────────────────
#  SHELLS
# ─────────────────────────────────────────────────────
shell-backend: ## Open a bash shell inside the backend container
	@$(DOCKER_COMPOSE) exec backend bash

shell-frontend: ## Open a bash shell inside the frontend container
	@$(DOCKER_COMPOSE) exec frontend sh

shell-postgres: ## Open psql session in the postgres container
	@$(DOCKER_COMPOSE) exec postgres psql \
		-U $${POSTGRES_USER:-futurevip} \
		-d $${POSTGRES_DB:-future_vip}

shell-redis: ## Open redis-cli session in the redis container
	@$(DOCKER_COMPOSE) exec redis redis-cli

# ─────────────────────────────────────────────────────
#  CLEANUP
# ─────────────────────────────────────────────────────
clean: ## Remove containers, networks, and volumes (DESTROYS all data)
	@echo "$(RED)$(BOLD)WARNING: This will destroy all Docker volumes and data!$(RESET)"
	@read -p "Type 'yes' to confirm: " CONFIRM && [ "$$CONFIRM" = "yes" ] || exit 1
	@$(DOCKER_COMPOSE) down --volumes --remove-orphans
	@docker volume rm futurevip_postgres_data futurevip_redis_data futurevip_chroma_data futurevip_upload_data 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(RESET)"

clean-images: ## Remove built Docker images
	@docker rmi futurevip-backend futurevip-frontend 2>/dev/null || true
	@docker image prune -f

clean-cache: ## Remove Python/Node caches
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Caches cleared$(RESET)"

reset-dev: ## DANGER: Fully reset dev environment (stop, delete volumes, rebuild, re-seed)
	@chmod +x scripts/reset_dev.sh
	@./scripts/reset_dev.sh

# ─────────────────────────────────────────────────────
#  PRODUCTION HELPERS
# ─────────────────────────────────────────────────────
deploy-prod: ## Deploy to production (builds and pushes images)
	@echo "$(BOLD)$(BLUE)Deploying to production...$(RESET)"
	@git push origin main

prod-up: ## Start production stack
	@$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
	@$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs: ## Tail production logs
	@$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=100
