#!/usr/bin/env bash
# =============================================================================
#  FUTURE VIP — PostgreSQL Backup Script
#  Usage: ./scripts/backup.sh [--s3] [--s3-bucket my-bucket] [--keep-local 7]
#  Creates timestamped compressed dump; optionally uploads to S3.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[BACKUP]${NC}  $*"; }
log_success() { echo -e "${GREEN}[BACKUP]${NC}  $*"; }
log_warn()    { echo -e "${YELLOW}[BACKUP]${NC}  $*"; }
log_error()   { echo -e "${RED}[BACKUP]${NC}  $*" >&2; }

die() { log_error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── Defaults ─────────────────────────────────────────────────────────────────
UPLOAD_TO_S3=false
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
S3_PREFIX="${BACKUP_S3_PREFIX:-futurevip/backups}"
KEEP_LOCAL_DAYS="${BACKUP_KEEP_LOCAL_DAYS:-7}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ─── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3)            UPLOAD_TO_S3=true; shift ;;
        --s3-bucket)     S3_BUCKET="$2"; UPLOAD_TO_S3=true; shift 2 ;;
        --s3-prefix)     S3_PREFIX="$2"; shift 2 ;;
        --keep-local)    KEEP_LOCAL_DAYS="$2"; shift 2 ;;
        --backup-dir)    BACKUP_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--s3] [--s3-bucket BUCKET] [--s3-prefix PREFIX] [--keep-local DAYS]"
            exit 0
            ;;
        *)
            log_warn "Unknown argument: $1"; shift ;;
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

# Detect docker compose
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

# ─── Setup backup dir ─────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

DUMP_FILENAME="futurevip_${PGDATABASE}_${TIMESTAMP}.dump"
DUMP_FILEPATH="$BACKUP_DIR/$DUMP_FILENAME"
COMPRESSED_FILEPATH="${DUMP_FILEPATH}.gz"

log_info "Starting backup of database: $PGDATABASE"
log_info "Timestamp:  $TIMESTAMP"
log_info "Output dir: $BACKUP_DIR"

# =============================================================================
#  STEP 1: Create pg_dump
# =============================================================================
log_info "Running pg_dump (custom format)..."

if [[ -n "$DOCKER_COMPOSE" ]]; then
    cd "$PROJECT_ROOT"
    # Check if postgres container is running
    POSTGRES_RUNNING=$($DOCKER_COMPOSE ps --status running postgres 2>/dev/null | grep -c "postgres" || true)

    if [[ "$POSTGRES_RUNNING" -gt 0 ]]; then
        $DOCKER_COMPOSE exec -T postgres \
            pg_dump -U "$PGUSER" -d "$PGDATABASE" \
            --format=custom \
            --compress=0 \
            --blobs \
            --verbose 2>/dev/null > "$DUMP_FILEPATH"
    else
        die "Postgres container is not running. Start it with: docker compose up -d postgres"
    fi
elif command -v pg_dump &>/dev/null; then
    pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$PGDATABASE" \
        --format=custom \
        --compress=0 \
        --blobs \
        --verbose \
        --file="$DUMP_FILEPATH"
else
    die "pg_dump not found. Install postgresql-client or use Docker."
fi

DUMP_SIZE=$(du -sh "$DUMP_FILEPATH" | cut -f1)
log_success "Dump created: $DUMP_FILENAME ($DUMP_SIZE)"

# =============================================================================
#  STEP 2: Compress
# =============================================================================
log_info "Compressing backup..."
gzip -9 "$DUMP_FILEPATH"
COMPRESSED_SIZE=$(du -sh "$COMPRESSED_FILEPATH" | cut -f1)
log_success "Compressed: $DUMP_FILENAME.gz ($COMPRESSED_SIZE)"

# =============================================================================
#  STEP 3: Generate checksum
# =============================================================================
log_info "Generating SHA-256 checksum..."
CHECKSUM_FILE="${COMPRESSED_FILEPATH}.sha256"
sha256sum "$COMPRESSED_FILEPATH" > "$CHECKSUM_FILE"
log_success "Checksum: $CHECKSUM_FILE"

# =============================================================================
#  STEP 4: Upload to S3 (optional)
# =============================================================================
if [[ "$UPLOAD_TO_S3" == "true" ]]; then
    if [[ -z "$S3_BUCKET" ]]; then
        die "--s3 specified but --s3-bucket is not set and BACKUP_S3_BUCKET env var is not set"
    fi

    if ! command -v aws &>/dev/null; then
        die "AWS CLI not found. Install from https://aws.amazon.com/cli/"
    fi

    S3_PATH="s3://${S3_BUCKET}/${S3_PREFIX}/${DUMP_FILENAME}.gz"
    S3_CHECKSUM_PATH="s3://${S3_BUCKET}/${S3_PREFIX}/${DUMP_FILENAME}.gz.sha256"

    log_info "Uploading to S3: $S3_PATH"

    aws s3 cp "$COMPRESSED_FILEPATH" "$S3_PATH" \
        --storage-class STANDARD_IA \
        --metadata "db=${PGDATABASE},timestamp=${TIMESTAMP}" \
        --no-progress

    aws s3 cp "$CHECKSUM_FILE" "$S3_CHECKSUM_PATH" --no-progress

    log_success "Uploaded to S3: $S3_PATH"

    # Tag the object with environment info
    aws s3api put-object-tagging \
        --bucket "$S3_BUCKET" \
        --key "${S3_PREFIX}/${DUMP_FILENAME}.gz" \
        --tagging "TagSet=[{Key=Project,Value=FutureVIP},{Key=Environment,Value=${ENVIRONMENT:-production}}]" \
        2>/dev/null || log_warn "Could not add S3 tags (non-fatal)"
fi

# =============================================================================
#  STEP 5: Clean up old local backups
# =============================================================================
log_info "Removing local backups older than $KEEP_LOCAL_DAYS days..."
CLEANED=$(find "$BACKUP_DIR" -name "futurevip_*.dump.gz" -mtime +"$KEEP_LOCAL_DAYS" -print -delete | wc -l)
find "$BACKUP_DIR" -name "futurevip_*.dump.gz.sha256" -mtime +"$KEEP_LOCAL_DAYS" -delete || true
log_success "Removed $CLEANED old backup(s)"

# =============================================================================
#  STEP 6: Restore instructions
# =============================================================================
echo ""
log_success "Backup complete!"
echo ""
echo "  Backup file:  $COMPRESSED_FILEPATH"
echo "  Size:         $COMPRESSED_SIZE"
echo ""
echo "  To restore:"
echo "    gunzip $COMPRESSED_FILEPATH"
echo "    pg_restore -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE --clean --if-exists $DUMP_FILEPATH"
echo ""
