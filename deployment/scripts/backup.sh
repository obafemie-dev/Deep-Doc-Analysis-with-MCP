#!/bin/bash

# ============================================================================
# Deep-Doc-Analysis Automated Backup Script
# ============================================================================
#
# PURPOSE:
#   Automated backup of analytics database, uploads, and Metabase data
#
# USAGE:
#   ./backup.sh                    # Run backup manually
#   ./backup.sh --full             # Force full backup (not incremental)
#   ./backup.sh --verify           # Verify last backup integrity
#
# INSTALLATION:
#   1. Copy to: /opt/deepdoc/scripts/backup.sh
#   2. Make executable: chmod +x /opt/deepdoc/scripts/backup.sh
#   3. Add to crontab: crontab -e
#      # Daily backup at 2 AM
#      0 2 * * * /opt/deepdoc/scripts/backup.sh >> /var/log/deepdoc-backup.log 2>&1
#
# REQUIREMENTS:
#   - Docker and Docker Compose installed
#   - Write access to backup directory
#   - Optional: rsync for off-site backups
#
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

# Directories
BACKUP_DIR="${BACKUP_DIR:-/opt/deepdoc/backups}"
DATA_DIR="/opt/deepdoc/data"
UPLOADS_DIR="/opt/deepdoc/uploads"
LOGS_DIR="/opt/deepdoc/logs"

# Container names
BACKEND_CONTAINER="deep-doc-backend"
METABASE_CONTAINER="deep-doc-metabase"

# Backup retention (days)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Timestamp for backup files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)

# Alert email (optional)
ALERT_EMAIL="${ALERT_EMAIL:-}"

# Log file
LOG_FILE="/var/log/deepdoc-backup.log"

# ============================================================================
# Functions
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
    send_alert "BACKUP FAILED" "$1"
    exit 1
}

send_alert() {
    local subject="$1"
    local message="$2"

    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "[DeepDoc] $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

check_dependencies() {
    log "Checking dependencies..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
    fi

    # Check if containers exist
    if ! docker ps -a | grep -q "$BACKEND_CONTAINER"; then
        error "Backend container not found"
    fi

    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"

    log "Dependencies check passed"
}

backup_analytics_db() {
    log "Backing up analytics database..."

    local db_backup_dir="$BACKUP_DIR/analytics"
    mkdir -p "$db_backup_dir"

    # Copy analytics.db from backend container
    if docker exec "$BACKEND_CONTAINER" test -f /app/analytics.db; then
        docker cp "$BACKEND_CONTAINER:/app/analytics.db" \
            "$db_backup_dir/analytics_${TIMESTAMP}.db" || \
            error "Failed to backup analytics database"

        # Get file size
        local size=$(du -h "$db_backup_dir/analytics_${TIMESTAMP}.db" | cut -f1)
        log "Analytics database backed up successfully ($size)"

        # Create a 'latest' symlink
        ln -sf "$db_backup_dir/analytics_${TIMESTAMP}.db" \
            "$db_backup_dir/analytics_latest.db"
    else
        log "WARNING: Analytics database not found, skipping..."
    fi
}

backup_uploads() {
    log "Backing up uploaded files..."

    local uploads_backup_dir="$BACKUP_DIR/uploads"
    mkdir -p "$uploads_backup_dir"

    if [ -d "$UPLOADS_DIR" ] && [ "$(ls -A $UPLOADS_DIR 2>/dev/null)" ]; then
        # Create tar.gz archive of uploads
        tar -czf "$uploads_backup_dir/uploads_${TIMESTAMP}.tar.gz" \
            -C "$(dirname $UPLOADS_DIR)" "$(basename $UPLOADS_DIR)" || \
            error "Failed to backup uploads"

        # Get file size and count
        local size=$(du -h "$uploads_backup_dir/uploads_${TIMESTAMP}.tar.gz" | cut -f1)
        local count=$(find "$UPLOADS_DIR" -type f | wc -l)
        log "Uploaded files backed up successfully ($count files, $size)"

        # Create a 'latest' symlink
        ln -sf "$uploads_backup_dir/uploads_${TIMESTAMP}.tar.gz" \
            "$uploads_backup_dir/uploads_latest.tar.gz"
    else
        log "No uploads to backup"
    fi
}

backup_metabase() {
    log "Backing up Metabase data..."

    local metabase_backup_dir="$BACKUP_DIR/metabase"
    mkdir -p "$metabase_backup_dir"

    # Copy Metabase H2 database
    if docker exec "$METABASE_CONTAINER" test -d /metabase-data; then
        # Create temporary directory in container
        docker exec "$METABASE_CONTAINER" mkdir -p /tmp/metabase-backup

        # Copy database files to temp directory
        docker exec "$METABASE_CONTAINER" sh -c \
            "cp -r /metabase-data/* /tmp/metabase-backup/" || \
            error "Failed to copy Metabase data in container"

        # Tar the backup inside container
        docker exec "$METABASE_CONTAINER" sh -c \
            "cd /tmp && tar -czf metabase-backup.tar.gz metabase-backup/" || \
            error "Failed to create Metabase tar archive"

        # Copy tar from container to host
        docker cp "$METABASE_CONTAINER:/tmp/metabase-backup.tar.gz" \
            "$metabase_backup_dir/metabase_${TIMESTAMP}.tar.gz" || \
            error "Failed to copy Metabase backup from container"

        # Cleanup temp files in container
        docker exec "$METABASE_CONTAINER" sh -c \
            "rm -rf /tmp/metabase-backup /tmp/metabase-backup.tar.gz" || true

        # Get file size
        local size=$(du -h "$metabase_backup_dir/metabase_${TIMESTAMP}.tar.gz" | cut -f1)
        log "Metabase data backed up successfully ($size)"

        # Create a 'latest' symlink
        ln -sf "$metabase_backup_dir/metabase_${TIMESTAMP}.tar.gz" \
            "$metabase_backup_dir/metabase_latest.tar.gz"
    else
        log "WARNING: Metabase data not found, skipping..."
    fi
}

backup_docker_compose() {
    log "Backing up Docker Compose configuration..."

    local config_backup_dir="$BACKUP_DIR/config"
    mkdir -p "$config_backup_dir"

    # Find docker-compose files
    local compose_dir="$(dirname $(dirname $(readlink -f $0)))/../.."

    if [ -f "$compose_dir/docker-compose.prod.yml" ]; then
        cp "$compose_dir/docker-compose.prod.yml" \
            "$config_backup_dir/docker-compose.prod_${TIMESTAMP}.yml"
        log "Docker Compose configuration backed up"
    fi

    # Backup Nginx configuration (if exists)
    if [ -f "/etc/nginx/sites-available/deepdoc" ]; then
        cp "/etc/nginx/sites-available/deepdoc" \
            "$config_backup_dir/nginx_${TIMESTAMP}.conf" || true
        log "Nginx configuration backed up"
    fi
}

cleanup_old_backups() {
    log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

    # Find and delete backups older than retention period
    find "$BACKUP_DIR" -type f -name "*.db" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.yml" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.conf" -mtime +$RETENTION_DAYS -delete

    log "Old backups cleaned up"
}

verify_backup() {
    log "Verifying backup integrity..."

    local verified=true

    # Verify analytics database
    if [ -f "$BACKUP_DIR/analytics/analytics_latest.db" ]; then
        if sqlite3 "$BACKUP_DIR/analytics/analytics_latest.db" "PRAGMA integrity_check;" | grep -q "ok"; then
            log "✓ Analytics database integrity OK"
        else
            log "✗ Analytics database integrity FAILED"
            verified=false
        fi
    fi

    # Verify tar archives
    for archive in "$BACKUP_DIR"/uploads/uploads_latest.tar.gz \
                   "$BACKUP_DIR"/metabase/metabase_latest.tar.gz; do
        if [ -f "$archive" ]; then
            if tar -tzf "$archive" >/dev/null 2>&1; then
                log "✓ Archive $(basename $archive) integrity OK"
            else
                log "✗ Archive $(basename $archive) integrity FAILED"
                verified=false
            fi
        fi
    done

    if [ "$verified" = true ]; then
        log "All backups verified successfully"
    else
        error "Backup verification failed"
    fi
}

create_backup_manifest() {
    log "Creating backup manifest..."

    local manifest_file="$BACKUP_DIR/manifest_${TIMESTAMP}.txt"

    cat > "$manifest_file" <<EOF
Deep-Doc-Analysis Backup Manifest
Generated: $(date)
Hostname: $(hostname)
Backup Directory: $BACKUP_DIR

=== ANALYTICS DATABASE ===
$(ls -lh $BACKUP_DIR/analytics/analytics_${TIMESTAMP}.db 2>/dev/null || echo "Not found")

=== UPLOADS ===
$(ls -lh $BACKUP_DIR/uploads/uploads_${TIMESTAMP}.tar.gz 2>/dev/null || echo "Not found")
Upload Count: $(tar -tzf $BACKUP_DIR/uploads/uploads_${TIMESTAMP}.tar.gz 2>/dev/null | wc -l || echo "0")

=== METABASE ===
$(ls -lh $BACKUP_DIR/metabase/metabase_${TIMESTAMP}.tar.gz 2>/dev/null || echo "Not found")

=== TOTAL BACKUP SIZE ===
$(du -sh $BACKUP_DIR)

=== DISK USAGE ===
$(df -h $BACKUP_DIR | tail -1)
EOF

    log "Backup manifest created: $manifest_file"
}

sync_to_offsite() {
    log "Syncing to off-site storage..."

    # Check if Hetzner Storage Box is configured
    if [ -n "${STORAGE_BOX_HOST:-}" ] && [ -n "${STORAGE_BOX_USER:-}" ]; then
        # Sync using rsync over SSH
        rsync -avz --delete \
            "$BACKUP_DIR/" \
            "${STORAGE_BOX_USER}@${STORAGE_BOX_HOST}:${STORAGE_BOX_PATH:-/backups/deepdoc/}" || \
            log "WARNING: Off-site sync failed"

        log "Off-site sync completed"
    else
        log "Off-site backup not configured, skipping..."
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "Starting Deep-Doc-Analysis backup"
    log "=========================================="

    # Parse arguments
    VERIFY_ONLY=false
    FULL_BACKUP=false

    for arg in "$@"; do
        case $arg in
            --verify)
                VERIFY_ONLY=true
                ;;
            --full)
                FULL_BACKUP=true
                ;;
        esac
    done

    # If verify only, run verification and exit
    if [ "$VERIFY_ONLY" = true ]; then
        verify_backup
        exit 0
    fi

    # Start backup process
    START_TIME=$(date +%s)

    # Pre-backup checks
    check_dependencies

    # Perform backups
    backup_analytics_db
    backup_uploads
    backup_metabase
    backup_docker_compose

    # Cleanup old backups
    cleanup_old_backups

    # Verify new backups
    verify_backup

    # Create manifest
    create_backup_manifest

    # Sync to off-site storage (optional)
    sync_to_offsite

    # Calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    log "=========================================="
    log "Backup completed successfully in ${DURATION}s"
    log "=========================================="

    # Send success notification
    send_alert "BACKUP SUCCESS" "Deep-Doc-Analysis backup completed in ${DURATION}s"
}

# Run main function
main "$@"
