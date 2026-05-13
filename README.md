# Krystal Studio — AI Chatbot Platform

Production-grade AI chatbot for a Tattoo, Piercing, and Dreadlock Studio. Built with FastAPI + PostgreSQL + pgvector (backend) and Next.js + TypeScript (frontend).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg |
| Database | PostgreSQL 16 + pgvector |
| AI | OpenAI GPT-4o-mini, text-embedding-3-large (3072d) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Hosting | Railway (API + DB), Vercel (frontend) |

## Prerequisites

- Python 3.12+
- Node.js 18+ / Bun
- PostgreSQL 16 with pgvector extension
- OpenAI API key

## Local Setup

```bash
# 1. Clone and install dependencies
cp .env.example .env          # then fill in real values
cd apps/api && pip install -r requirements.txt
cd apps/web && bun install

# 2. Start PostgreSQL (Docker or local)
make docker-up                # uses infra/docker/docker-compose.yml

# 3. Run migrations and seed data
make migrate
make seed

# 4. Start dev servers (two terminals)
make dev-api                  # http://localhost:8000
make dev-web                  # http://localhost:3000
```

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `JWT_SECRET` | Must be changed from default in production |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `ENVIRONMENT` | `development` or `production` |
| `SENTRY_DSN` | Optional Sentry DSN for error tracking |

## Testing

```bash
# Unit tests only (no DB required)
make test-api

# Unit + integration tests (requires PostgreSQL)
make test-api-integration

# Frontend
cd apps/web && bun run lint && bunx tsc --noEmit
```

## Project Structure

```
apps/
  api/              # FastAPI backend
    app/
      api/v1/       # Route handlers
      core/         # Config, security, rate limiting, logging
      db/models/    # SQLAlchemy models
      schemas/      # Pydantic request/response models
      services/     # Business logic (chat, RAG, leads)
    alembic/        # Database migrations
    tests/          # Unit + integration + AI eval tests
  web/              # Next.js frontend
    app/            # Pages and layouts
    components/     # React components
    lib/            # API client, utilities
scripts/            # Backup, seed scripts
docs/               # Plans, architecture docs
```

## Deployment

- **Backend**: Railway — auto-deploys from `main` branch. See `apps/api/Dockerfile`.
- **Frontend**: Vercel — auto-deploys from `main` branch. Root directory: `apps/web`.
- **Database**: Railway PostgreSQL with pgvector.

### Rollback

1. **API**: Redeploy previous Railway deployment from dashboard.
2. **Frontend**: Promote previous Vercel deployment in dashboard.
3. **Database**: Restore from backup (`scripts/backup_db.sh`) or `alembic downgrade -1` if reversible.

## Contributing

- Trunk-based development on `main`
- Conventional commits: `feat:`, `fix:`, `chore:`, `refactor:`
- All PRs must pass CI (lint + tests + migration check)
