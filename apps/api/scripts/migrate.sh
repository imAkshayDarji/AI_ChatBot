#!/usr/bin/env bash
set -euo pipefail

cd /app

if [[ "${DATABASE_URL}" == postgresql://* ]]; then
  export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
fi

python scripts/ensure_pgvector.py
python -m alembic upgrade head
