.PHONY: dev-api dev-web test-api lint migrate seed docker-up docker-down

# Backend
dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

test-api:
	cd apps/api && PYTHONPATH=. SKIP_INTEGRATION=1 python -m pytest app/tests/ -v

test-api-integration:
	cd apps/api && PYTHONPATH=. python -m pytest app/tests/integration -v

lint:
	cd apps/api && python -m ruff check app/ && cd ../../apps/web && pnpm lint

migrate:
	cd apps/api && PYTHONPATH=. alembic upgrade head

seed:
	cd apps/api && PYTHONPATH=. python scripts/seed_admin.py

# Frontend
dev-web:
	cd apps/web && pnpm dev

# Docker
docker-up:
	cd infra/docker && docker-compose up -d

docker-down:
	cd infra/docker && docker-compose down
