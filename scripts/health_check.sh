#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — Health Check Script
#  Usage: ./scripts/health_check.sh [--json] [--exit-on-failure]
#  Checks: PostgreSQL, Redis, ChromaDB, Backend API, Frontend
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Args ─────────────────────────────────────────────────────────────────────
JSON_OUTPUT=false
EXIT_ON_FAILURE=false

for arg in "$@"; do
    case $arg in
        --json)             JSON_OUTPUT=true ;;
        --exit-on-failure)  EXIT_ON_FAILURE=true ;;
        --help|-h)
            echo "Usage: $0 [--json] [--exit-on-failure]"
            exit 0
            ;;
    esac
done

# ─── Load env ─────────────────────────────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/backend/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$PROJECT_ROOT/backend/.env" | grep -v '^$') 2>/dev/null || true
    set +a
fi

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
CHROMA_URL="http://localhost:${CHROMA_PORT:-8001}"
POSTGRES_USER="${POSTGRES_USER:-futurevip}"
POSTGRES_DB="${POSTGRES_DB:-future_vip}"

# ─── Detect docker compose ────────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

# ─── Health check state ───────────────────────────────────────────────────────
declare -A SERVICE_STATUS
declare -A SERVICE_LATENCY
declare -A SERVICE_DETAILS
ALL_HEALTHY=true

# ─── Check helpers ────────────────────────────────────────────────────────────
check_http() {
    local service="$1"
    local url="$2"
    local expected_code="${3:-200}"
    local timeout="${4:-5}"

    local start_ms
    start_ms=$(date +%s%3N)

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time "$timeout" \
        --connect-timeout 3 \
        "$url" 2>/dev/null) || http_code="000"

    local end_ms
    end_ms=$(date +%s%3N)
    local latency_ms=$((end_ms - start_ms))

    SERVICE_LATENCY[$service]="${latency_ms}ms"

    if [[ "$http_code" == "$expected_code" ]]; then
        SERVICE_STATUS[$service]="healthy"
        SERVICE_DETAILS[$service]="HTTP $http_code (${latency_ms}ms)"
        return 0
    else
        SERVICE_STATUS[$service]="unhealthy"
        SERVICE_DETAILS[$service]="HTTP $http_code — expected $expected_code (${latency_ms}ms)"
        ALL_HEALTHY=false
        return 1
    fi
}

check_docker_container() {
    local service="$1"
    local container="$2"

    if [[ -z "$DOCKER_COMPOSE" ]]; then
        SERVICE_STATUS[$service]="unknown"
        SERVICE_DETAILS[$service]="Docker Compose not available"
        return 1
    fi

    local state
    state=$(cd "$PROJECT_ROOT" && $DOCKER_COMPOSE ps --status running "$container" 2>/dev/null | grep -c "$container" || echo "0")

    if [[ "$state" -gt 0 ]]; then
        SERVICE_STATUS[$service]="running"
        return 0
    else
        SERVICE_STATUS[$service]="not_running"
        SERVICE_DETAILS[$service]="Container not running"
        ALL_HEALTHY=false
        return 1
    fi
}

print_service_status() {
    local service="$1"
    local status="${SERVICE_STATUS[$service]:-unknown}"
    local details="${SERVICE_DETAILS[$service]:-}"

    if [[ "$status" == "healthy" ]] || [[ "$status" == "running" ]]; then
        echo -e "  ${GREEN}[OK]${NC}    ${BOLD}$service${NC} — $details"
    elif [[ "$status" == "unknown" ]]; then
        echo -e "  ${YELLOW}[?]${NC}     ${BOLD}$service${NC} — $details"
    else
        echo -e "  ${RED}[FAIL]${NC}  ${BOLD}$service${NC} — $details"
    fi
}

# =============================================================================
#  Run Health Checks
# =============================================================================
if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}FUTURE VIP — Service Health Check${NC}"
    echo -e "  Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo ""
fi

# ─── 1. PostgreSQL ────────────────────────────────────────────────────────────
if [[ -n "$DOCKER_COMPOSE" ]]; then
    if (cd "$PROJECT_ROOT" && $DOCKER_COMPOSE exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null); then
        SERVICE_STATUS[postgresql]="healthy"
        SERVICE_DETAILS[postgresql]="pg_isready OK"
    else
        SERVICE_STATUS[postgresql]="unhealthy"
        SERVICE_DETAILS[postgresql]="pg_isready failed"
        ALL_HEALTHY=false
    fi
elif command -v pg_isready &>/dev/null; then
    if pg_isready -h localhost -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null; then
        SERVICE_STATUS[postgresql]="healthy"
        SERVICE_DETAILS[postgresql]="pg_isready OK"
    else
        SERVICE_STATUS[postgresql]="unhealthy"
        SERVICE_DETAILS[postgresql]="pg_isready failed"
        ALL_HEALTHY=false
    fi
else
    SERVICE_STATUS[postgresql]="unknown"
    SERVICE_DETAILS[postgresql]="pg_isready not available"
fi

# ─── 2. Redis ─────────────────────────────────────────────────────────────────
if [[ -n "$DOCKER_COMPOSE" ]]; then
    if (cd "$PROJECT_ROOT" && $DOCKER_COMPOSE exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"); then
        SERVICE_STATUS[redis]="healthy"
        SERVICE_DETAILS[redis]="PONG received"
    else
        SERVICE_STATUS[redis]="unhealthy"
        SERVICE_DETAILS[redis]="No PONG response"
        ALL_HEALTHY=false
    fi
elif command -v redis-cli &>/dev/null; then
    if redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q "PONG"; then
        SERVICE_STATUS[redis]="healthy"
        SERVICE_DETAILS[redis]="PONG received"
    else
        SERVICE_STATUS[redis]="unhealthy"
        SERVICE_DETAILS[redis]="No PONG response"
        ALL_HEALTHY=false
    fi
else
    SERVICE_STATUS[redis]="unknown"
    SERVICE_DETAILS[redis]="redis-cli not available"
fi

# ─── 3. ChromaDB ──────────────────────────────────────────────────────────────
check_http "chromadb" "${CHROMA_URL}/api/v1/heartbeat" "200" || true

# ─── 4. Backend API ───────────────────────────────────────────────────────────
check_http "backend_api" "${BACKEND_URL}/health" "200" || true

# Also check the OpenAPI schema endpoint
check_http "backend_openapi" "${BACKEND_URL}/openapi.json" "200" || true

# ─── 5. Frontend ──────────────────────────────────────────────────────────────
check_http "frontend" "${FRONTEND_URL}" "200" || true

# ─── 6. Celery Worker (via Docker) ────────────────────────────────────────────
if [[ -n "$DOCKER_COMPOSE" ]]; then
    CELERY_STATUS=$(cd "$PROJECT_ROOT" && $DOCKER_COMPOSE ps --status running celery_worker 2>/dev/null | grep -c "celery_worker" || echo "0")
    if [[ "$CELERY_STATUS" -gt 0 ]]; then
        SERVICE_STATUS[celery_worker]="running"
        SERVICE_DETAILS[celery_worker]="Container is running"
    else
        SERVICE_STATUS[celery_worker]="not_running"
        SERVICE_DETAILS[celery_worker]="Container not running"
        ALL_HEALTHY=false
    fi
else
    SERVICE_STATUS[celery_worker]="unknown"
    SERVICE_DETAILS[celery_worker]="Cannot check without Docker"
fi

# =============================================================================
#  Output
# =============================================================================
if [[ "$JSON_OUTPUT" == "true" ]]; then
    # JSON output
    echo "{"
    echo "  \"timestamp\": \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\","
    echo "  \"all_healthy\": $( [[ "$ALL_HEALTHY" == "true" ]] && echo "true" || echo "false" ),"
    echo "  \"services\": {"
    FIRST=true
    for service in postgresql redis chromadb backend_api backend_openapi frontend celery_worker; do
        status="${SERVICE_STATUS[$service]:-unknown}"
        details="${SERVICE_DETAILS[$service]:-}"
        [[ "$FIRST" == "false" ]] && echo ","
        echo -n "    \"$service\": {\"status\": \"$status\", \"details\": \"$details\"}"
        FIRST=false
    done
    echo ""
    echo "  }"
    echo "}"
else
    echo -e "${BOLD}Infrastructure:${NC}"
    print_service_status "postgresql"
    print_service_status "redis"
    print_service_status "chromadb"

    echo ""
    echo -e "${BOLD}Application:${NC}"
    print_service_status "backend_api"
    print_service_status "backend_openapi"
    print_service_status "frontend"
    print_service_status "celery_worker"

    echo ""
    if [[ "$ALL_HEALTHY" == "true" ]]; then
        echo -e "${GREEN}${BOLD}All services healthy${NC}"
    else
        echo -e "${RED}${BOLD}One or more services are unhealthy${NC}"
        echo ""
        echo "Troubleshooting:"
        echo "  docker compose logs --tail=50 <service>"
        echo "  docker compose ps"
        echo "  make logs"
    fi
fi

# Exit with error code if any service is unhealthy and --exit-on-failure
if [[ "$EXIT_ON_FAILURE" == "true" ]] && [[ "$ALL_HEALTHY" == "false" ]]; then
    exit 1
fi
