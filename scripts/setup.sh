#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — Full Environment Setup Script
#  Usage: ./scripts/setup.sh [--no-seed] [--no-frontend]
#  Idempotent: safe to run multiple times
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── Helpers ──────────────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

die() {
    log_error "$*"
    exit 1
}

# ─── Parse Args ───────────────────────────────────────────────────────────────
RUN_SEED=true
RUN_FRONTEND=true

for arg in "$@"; do
    case $arg in
        --no-seed)     RUN_SEED=false ;;
        --no-frontend) RUN_FRONTEND=false ;;
        --help|-h)
            echo "Usage: $0 [--no-seed] [--no-frontend]"
            exit 0
            ;;
        *)
            log_warn "Unknown argument: $arg"
            ;;
    esac
done

# ─── Project root ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║          FUTURE VIP — Environment Setup              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

cd "$PROJECT_ROOT"

# =============================================================================
#  STEP 1: Check Dependencies
# =============================================================================
log_info "Step 1/9 — Checking dependencies..."

check_command() {
    local cmd=$1
    local install_hint=${2:-"Please install $cmd"}
    if ! command -v "$cmd" &>/dev/null; then
        die "Required command not found: '$cmd'. $install_hint"
    fi
    log_success "$cmd found: $(command -v "$cmd")"
}

check_command "docker"        "Install from https://docs.docker.com/get-docker/"
check_command "docker"        "docker compose plugin required"
check_command "python3"       "Install Python 3.11+ from https://python.org"
check_command "openssl"       "Install openssl via your package manager"

# Verify docker compose v2 (plugin style)
if ! docker compose version &>/dev/null; then
    # Fall back to docker-compose v1
    if ! command -v docker-compose &>/dev/null; then
        die "Docker Compose not found. Install from https://docs.docker.com/compose/install/"
    fi
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

log_success "Docker Compose: $($DOCKER_COMPOSE version --short 2>/dev/null || echo 'v1')"

if [[ "$RUN_FRONTEND" == "true" ]]; then
    check_command "node" "Install Node.js 20+ from https://nodejs.org"
    check_command "npm"  "Install npm (bundled with Node.js)"
    log_success "Node.js: $(node --version)"
fi

# =============================================================================
#  STEP 2: Copy .env files
# =============================================================================
log_info "Step 2/9 — Setting up environment files..."

# Root .env
if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
    if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log_success "Created .env from .env.example"
    else
        log_warn ".env.example not found; creating minimal .env"
        touch "$PROJECT_ROOT/.env"
    fi
else
    log_info ".env already exists — skipping"
fi

# Backend .env
if [[ ! -f "$PROJECT_ROOT/backend/.env" ]]; then
    if [[ -f "$PROJECT_ROOT/backend/.env.example" ]]; then
        cp "$PROJECT_ROOT/backend/.env.example" "$PROJECT_ROOT/backend/.env"
        log_success "Created backend/.env from backend/.env.example"
    else
        cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/backend/.env"
        log_success "Copied root .env to backend/.env"
    fi
else
    log_info "backend/.env already exists — skipping"
fi

# =============================================================================
#  STEP 3: Generate SECRET_KEY
# =============================================================================
log_info "Step 3/9 — Generating cryptographic secrets..."

generate_secret() {
    openssl rand -hex 32
}

ENV_FILE="$PROJECT_ROOT/backend/.env"

update_env_var() {
    local key=$1
    local value=$2
    local file=$3

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # Only update if current value looks like a placeholder
        current=$(grep "^${key}=" "$file" | cut -d'=' -f2- | tr -d '"')
        if [[ "$current" == *"changeme"* ]] || [[ "$current" == *"generate"* ]] || [[ -z "$current" ]]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
            else
                sed -i "s|^${key}=.*|${key}=${value}|" "$file"
            fi
            log_success "Updated ${key} in $(basename "$file")"
        else
            log_info "${key} already set — skipping"
        fi
    else
        echo "${key}=${value}" >> "$file"
        log_success "Added ${key} to $(basename "$file")"
    fi
}

SECRET_KEY=$(generate_secret)
update_env_var "SECRET_KEY" "$SECRET_KEY" "$ENV_FILE"

# =============================================================================
#  STEP 4: Start infrastructure services
# =============================================================================
log_info "Step 4/9 — Starting infrastructure services (postgres, redis, chromadb)..."

$DOCKER_COMPOSE up -d postgres redis chromadb

log_success "Infrastructure containers started"

# =============================================================================
#  STEP 5: Wait for PostgreSQL to be ready
# =============================================================================
log_info "Step 5/9 — Waiting for PostgreSQL to be ready..."

MAX_RETRIES=30
RETRY_INTERVAL=3
RETRIES=0

POSTGRES_USER="${POSTGRES_USER:-futurevip}"
POSTGRES_DB="${POSTGRES_DB:-future_vip}"

# Load from .env if present
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$')
    set +a
fi

until $DOCKER_COMPOSE exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [[ $RETRIES -ge $MAX_RETRIES ]]; then
        die "PostgreSQL did not become ready after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
    fi
    echo -n "."
    sleep $RETRY_INTERVAL
done
echo ""
log_success "PostgreSQL is ready"

# =============================================================================
#  STEP 6: Wait for Redis
# =============================================================================
log_info "Step 6/9 — Verifying Redis is ready..."

REDIS_RETRIES=0
until $DOCKER_COMPOSE exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; do
    REDIS_RETRIES=$((REDIS_RETRIES + 1))
    if [[ $REDIS_RETRIES -ge 15 ]]; then
        die "Redis did not become ready in time"
    fi
    sleep 2
done
log_success "Redis is ready"

# =============================================================================
#  STEP 7: Run Database Migrations
# =============================================================================
log_info "Step 7/9 — Running database migrations..."

"$SCRIPT_DIR/migrate.sh"

# =============================================================================
#  STEP 8: Seed Database
# =============================================================================
if [[ "$RUN_SEED" == "true" ]]; then
    log_info "Step 8/9 — Seeding database with sample data..."
    "$SCRIPT_DIR/seed.sh"
else
    log_info "Step 8/9 — Skipping database seed (--no-seed)"
fi

# =============================================================================
#  STEP 9: Start Application Services
# =============================================================================
log_info "Step 9/9 — Starting application services..."

$DOCKER_COMPOSE up -d backend celery_worker celery_beat flower

if [[ "$RUN_FRONTEND" == "true" ]]; then
    $DOCKER_COMPOSE up -d frontend
fi

# Wait briefly for backend to initialize
sleep 5

# =============================================================================
#  Summary
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║           FUTURE VIP Setup Complete!                 ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Service URLs:${NC}"
echo -e "  Frontend:        ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend API:     ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:        ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  Flower Monitor:  ${GREEN}http://localhost:5555${NC}"
echo -e "  ChromaDB:        ${GREEN}http://localhost:8001${NC}"
echo ""
echo -e "${BOLD}Demo Credentials:${NC}"
echo -e "  Admin:  admin@futurevip.ai / FutureVIP@Admin2025!"
echo -e "  Demo:   demo@futurevip.ai  / DemoUser@2025!"
echo ""
echo -e "${BOLD}Useful commands:${NC}"
echo -e "  make logs          # Tail all service logs"
echo -e "  make stop          # Stop all services"
echo -e "  make health        # Run health checks"
echo -e "  make shell-backend # Shell into backend container"
echo ""
