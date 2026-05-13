#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
FILENAME="krystal_studio_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

echo "==> Starting backup → ${FILEPATH}"

pg_dump "${DATABASE_URL}" | gzip > "$FILEPATH"

SIZE=$(wc -c < "$FILEPATH")
if [ "$SIZE" -lt 1024 ]; then
    echo "ERROR: Backup file is suspiciously small (${SIZE} bytes). Possible failure." >&2
    rm -f "$FILEPATH"
    exit 1
fi

echo "==> Backup complete: ${FILENAME} (${SIZE} bytes)"
