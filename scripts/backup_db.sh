#!/bin/bash
set -euo pipefail

echo "Starting database backup..."
echo "Usage: Set DATABASE_URL and run: pg_dump $DATABASE_URL > backup.sql"
