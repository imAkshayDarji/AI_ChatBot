# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python scripts/ensure_pgvector.py 2>&1; python -m alembic upgrade head 2>&1; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
