#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — Reset Development Environment
#  Usage: ./scripts/reset_dev.sh [--yes] [--keep-images]
#  WARNING: This DESTROYS all local data (volumes). Dev use only!
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[RESET]${NC}   $*"; }
log_success() { echo -e "${GREEN}[RESET]${NC}   $*"; }
log_warn()    { echo -e "${YELLOW}[RESET]${NC}   $*"; }
log_error()   { echo -e "${RED}[RESET]${NC}   $*" >&2; }

die() { log_error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Args ─────────────────────────────────────────────────────────────────────
SKIP_CONFIRM=false
KEEP_IMAGES=false
NO_SEED=false

for arg in "$@"; do
    case $arg in
        --yes)          SKIP_CONFIRM=true ;;
        --keep-images)  KEEP_IMAGES=true ;;
        --no-seed)      NO_SEED=true ;;
        --help|-h)
            echo ""
            echo "  FUTURE VIP — Reset Development Environment"
            echo ""
            echo "  Usage: $0 [--yes] [--keep-images] [--no-seed]"
            echo ""
            echo "  Options:"
            echo "    --yes          Skip confirmation prompt"
            echo "    --keep-images  Do not remove Docker images (faster rebuild)"
            echo "    --no-seed      Do not re-seed after recreating"
            echo ""
            echo "  WARNING: This will DELETE all local data volumes!"
            echo ""
            exit 0
            ;;
        *)
            log_warn "Unknown argument: $arg"
            ;;
    esac
done

# ─── Detect docker compose ────────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    die "Docker Compose not found"
fi

# ─── Confirm ──────────────────────────────────────────────────────────────────
if [[ "$SKIP_CONFIRM" == "false" ]]; then
    echo -e "${RED}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║           ⚠  DESTRUCTIVE OPERATION  ⚠               ║"
    echo "  ║                                                       ║"
    echo "  ║  This will:                                           ║"
    echo "  ║  • Stop all running containers                        ║"
    echo "  ║  • DELETE all Docker volumes (all local data)         ║"
    echo "  ║  • Rebuild and restart all services                   ║"
    echo "  ║  • Re-seed the database with sample data              ║"
    echo "  ║                                                       ║"
    echo "  ║  This is for DEVELOPMENT environments ONLY.           ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    read -rp "  Type 'RESET' to confirm: " CONFIRM
    if [[ "$CONFIRM" != "RESET" ]]; then
        log_info "Reset cancelled."
        exit 0
    fi
fi

cd "$PROJECT_ROOT"

# =============================================================================
#  STEP 1: Stop all containers
# =============================================================================
log_info "Step 1/6 — Stopping all containers..."
$DOCKER_COMPOSE down --remove-orphans || true
log_success "Containers stopped"

# =============================================================================
#  STEP 2: Remove volumes
# =============================================================================
log_info "Step 2/6 — Removing all data volumes..."

# Remove named volumes
VOLUMES=(
    "futurevip_postgres_data"
    "futurevip_redis_data"
    "futurevip_chroma_data"
    "futurevip_upload_data"
)

for volume in "${VOLUMES[@]}"; do
    if docker volume inspect "$volume" &>/dev/null 2>&1; then
        docker volume rm "$volume" && log_success "Removed volume: $volume"
    else
        log_info "Volume not found (skipping): $volume"
    fi
done

# Also remove any compose-managed volumes
$DOCKER_COMPOSE down --volumes 2>/dev/null || true

log_success "Volumes removed"

# =============================================================================
#  STEP 3: Remove Docker images (optional)
# =============================================================================
if [[ "$KEEP_IMAGES" == "false" ]]; then
    log_info "Step 3/6 — Removing built images..."
    IMAGES=(
        "futurevip_backend"
        "futurevip-backend"
        "futurevip_frontend"
        "futurevip-frontend"
    )
    for image in "${IMAGES[@]}"; do
        if docker image inspect "$image" &>/dev/null 2>&1; then
            docker rmi "$image" && log_success "Removed image: $image"
        fi
    done
    log_success "Images removed (will be rebuilt)"
else
    log_info "Step 3/6 — Skipping image removal (--keep-images)"
fi

# =============================================================================
#  STEP 4: Clean local temp files
# =============================================================================
log_info "Step 4/6 — Cleaning local temporary files..."

# Remove Python cache
find "$PROJECT_ROOT/backend" -type d -name "__pycache__"  -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/backend" -type f -name "*.pyc"         -delete 2>/dev/null || true
find "$PROJECT_ROOT/backend" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Remove Alembic cache
find "$PROJECT_ROOT/backend" -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

log_success "Temporary files cleaned"

# =============================================================================
#  STEP 5: Rebuild and restart
# =============================================================================
log_info "Step 5/6 — Building and starting services..."

# Start infrastructure
$DOCKER_COMPOSE up -d --build postgres redis chromadb

log_info "Waiting for PostgreSQL to be ready..."
RETRIES=0
MAX_RETRIES=30

until $DOCKER_COMPOSE exec -T postgres pg_isready \
    -U "${POSTGRES_USER:-futurevip}" \
    -d "${POSTGRES_DB:-future_vip}" &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [[ $RETRIES -ge $MAX_RETRIES ]]; then
        die "PostgreSQL did not start in time"
    fi
    echo -n "."
    sleep 2
done
echo ""
log_success "PostgreSQL is ready"

log_info "Waiting for Redis..."
REDIS_RETRIES=0
until $DOCKER_COMPOSE exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; do
    REDIS_RETRIES=$((REDIS_RETRIES + 1))
    if [[ $REDIS_RETRIES -ge 15 ]]; then
        die "Redis did not start in time"
    fi
    sleep 2
done
log_success "Redis is ready"

# Run migrations
log_info "Running database migrations..."
"$SCRIPT_DIR/migrate.sh"

# =============================================================================
#  STEP 6: Seed database
# =============================================================================
if [[ "$NO_SEED" == "false" ]]; then
    log_info "Step 6/6 — Seeding database..."
    "$SCRIPT_DIR/seed.sh"
else
    log_info "Step 6/6 — Skipping seed (--no-seed)"
fi

# Start application services
$DOCKER_COMPOSE up -d --build backend celery_worker celery_beat flower frontend

# =============================================================================
#  Summary
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}Development environment reset complete!${NC}"
echo ""
echo "  Frontend:       http://localhost:3000"
echo "  Backend API:    http://localhost:8000"
echo "  API Docs:       http://localhost:8000/docs"
echo "  Flower:         http://localhost:5555"
echo ""
echo "  Admin:   admin@futurevip.ai / FutureVIP@Admin2025!"
echo "  Demo:    demo@futurevip.ai  / DemoUser@2025!"
echo ""
