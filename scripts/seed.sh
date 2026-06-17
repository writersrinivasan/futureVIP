#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — Database Seed Script
#  Usage: ./scripts/seed.sh [--reset]
#  Seeds the database with demo/development data from database/002_seed.sql
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[SEED]${NC}    $*"; }
log_success() { echo -e "${GREEN}[SEED]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[SEED]${NC}    $*"; }
log_error()   { echo -e "${RED}[SEED]${NC}    $*" >&2; }

die() { log_error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SEED_FILE="$PROJECT_ROOT/database/002_seed.sql"

# ─── Args ─────────────────────────────────────────────────────────────────────
RESET_FIRST=false
for arg in "$@"; do
    case $arg in
        --reset)  RESET_FIRST=true ;;
        --help|-h)
            echo "Usage: $0 [--reset]"
            echo "  --reset  Truncate all tables before seeding"
            exit 0
            ;;
    esac
done

# ─── Load env ─────────────────────────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/backend/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$PROJECT_ROOT/backend/.env" | grep -v '^$')
    set +a
fi

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-futurevip}"
PGPASSWORD="${POSTGRES_PASSWORD:-changeme_in_prod}"
PGDATABASE="${POSTGRES_DB:-future_vip}"

export PGPASSWORD

# ─── Detect runner ────────────────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

run_sql_file() {
    local sql_file="$1"
    local label
    label=$(basename "$sql_file")

    if [[ -n "$DOCKER_COMPOSE" ]]; then
        log_info "Applying $label via Docker..."
        cd "$PROJECT_ROOT"
        $DOCKER_COMPOSE exec -T postgres \
            psql -U "$PGUSER" -d "$PGDATABASE" -f "/docker-entrypoint-initdb.d/$(basename "$sql_file")"
    elif command -v psql &>/dev/null; then
        log_info "Applying $label via psql..."
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f "$sql_file"
    else
        die "Neither docker compose nor psql found. Cannot seed database."
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────
[[ -f "$SEED_FILE" ]] || die "Seed file not found: $SEED_FILE"

log_info "Starting database seed..."
log_info "Seed file: $SEED_FILE"

if [[ "$RESET_FIRST" == "true" ]]; then
    log_warn "RESET mode: truncating all data tables..."

    TRUNCATE_SQL="TRUNCATE TABLE
        audit_logs,
        interview_sessions,
        career_roadmaps,
        user_skills,
        notifications,
        applications,
        job_matches,
        jobs,
        resumes,
        users
        RESTART IDENTITY CASCADE;"

    if [[ -n "$DOCKER_COMPOSE" ]]; then
        cd "$PROJECT_ROOT"
        $DOCKER_COMPOSE exec -T postgres psql -U "$PGUSER" -d "$PGDATABASE" -c "$TRUNCATE_SQL"
    elif command -v psql &>/dev/null; then
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "$TRUNCATE_SQL"
    fi

    log_warn "All data tables truncated"
fi

# Apply seed SQL
if [[ -n "$DOCKER_COMPOSE" ]]; then
    cd "$PROJECT_ROOT"
    log_info "Copying seed file into postgres container..."
    $DOCKER_COMPOSE exec -T postgres psql -U "$PGUSER" -d "$PGDATABASE" < "$SEED_FILE"
elif command -v psql &>/dev/null; then
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f "$SEED_FILE"
else
    die "Cannot run seed: no psql or docker compose available"
fi

log_success "Database seeded successfully"
log_info "Admin:  admin@futurevip.ai / FutureVIP@Admin2025!"
log_info "Demo:   demo@futurevip.ai  / DemoUser@2025!"
