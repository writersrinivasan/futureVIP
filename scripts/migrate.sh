#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — Run Alembic Database Migrations
#  Usage: ./scripts/migrate.sh [revision] [--dry-run]
#  Default: runs all pending migrations (alembic upgrade head)
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[MIGRATE]${NC} $*"; }
log_success() { echo -e "${GREEN}[MIGRATE]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[MIGRATE]${NC} $*"; }
log_error()   { echo -e "${RED}[MIGRATE]${NC} $*" >&2; }

die() { log_error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Parse args ───────────────────────────────────────────────────────────────
REVISION="head"
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [revision] [--dry-run]"
            echo "  revision   Alembic revision target (default: head)"
            echo "  --dry-run  Show what would run without executing"
            exit 0
            ;;
        *)
            REVISION="$arg"
            ;;
    esac
done

# ─── Determine how to run migrations ──────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/backend/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$PROJECT_ROOT/backend/.env" | grep -v '^$')
    set +a
fi

# Detect docker compose command
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

run_alembic() {
    local cmd="$*"

    if [[ -n "$DOCKER_COMPOSE" ]]; then
        log_info "Running via Docker: alembic $cmd"
        cd "$PROJECT_ROOT"
        $DOCKER_COMPOSE exec -T backend sh -c "cd /app && alembic $cmd"
    elif command -v alembic &>/dev/null; then
        log_info "Running locally: alembic $cmd"
        cd "$PROJECT_ROOT/backend"
        alembic $cmd
    else
        # Fallback: apply SQL directly via psql
        log_warn "Alembic not found. Applying raw SQL migrations via psql..."
        apply_raw_sql
    fi
}

apply_raw_sql() {
    local PGHOST="${POSTGRES_HOST:-localhost}"
    local PGPORT="${POSTGRES_PORT:-5432}"
    local PGUSER="${POSTGRES_USER:-futurevip}"
    local PGPASSWORD="${POSTGRES_PASSWORD:-changeme_in_prod}"
    local PGDATABASE="${POSTGRES_DB:-future_vip}"

    export PGPASSWORD

    log_info "Applying SQL migrations from database/"

    for sql_file in "$PROJECT_ROOT/database/"*.sql; do
        if [[ -f "$sql_file" ]]; then
            filename=$(basename "$sql_file")
            log_info "Applying: $filename"
            if [[ "$DRY_RUN" == "true" ]]; then
                log_warn "[DRY RUN] Would apply: $filename"
            else
                psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f "$sql_file" \
                    && log_success "Applied: $filename" \
                    || die "Failed to apply: $filename"
            fi
        fi
    done
}

# ─── Main ─────────────────────────────────────────────────────────────────────
log_info "Starting database migrations (target: $REVISION)..."

if [[ "$DRY_RUN" == "true" ]]; then
    log_warn "DRY RUN mode — no changes will be made"
fi

cd "$PROJECT_ROOT"

# Check if backend container is running
if [[ -n "$DOCKER_COMPOSE" ]]; then
    BACKEND_STATUS=$($DOCKER_COMPOSE ps --status running backend 2>/dev/null | grep -c "backend" || true)
    if [[ "$BACKEND_STATUS" -eq 0 ]]; then
        log_warn "Backend container not running. Attempting to apply raw SQL..."
        apply_raw_sql
        exit 0
    fi
fi

if [[ "$DRY_RUN" == "true" ]]; then
    run_alembic "show $REVISION"
else
    run_alembic "upgrade $REVISION"
fi

log_success "Migrations complete (target: $REVISION)"
