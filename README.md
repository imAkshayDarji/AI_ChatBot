# Krystal Studio — AI Chatbot Platform

Production-grade AI chatbot for a tattoo, piercing, and dreadlock studio. The stack is **FastAPI** + **PostgreSQL** + **pgvector** (API and RAG) and **Next.js** + **TypeScript** + **Tailwind** (marketing site + embedded chat widget + admin console).

---

## Features

| Area | Capability |
|------|-------------|
| **Chat** | Multilingual UX (English / Hindi / Gujarati-oriented copy), streamed replies, studio handoffs, quick replies |
| **RAG** | Hybrid retrieval over curated studio knowledge — vector similarity (`pgvector`) + full-text |
| **Safety** | Medical / pricing / policy guardrails, prompt-injection defenses (see `docs/AI_SYSTEM.md`) |
| **Leads** | Capture contact intent from conversations |
| **Admin** | JWT auth, knowledge ingestion & reindex, conversations, leads, analytics, settings |
| **Ops** | Structured logging with PII-aware redaction, health checks, rate limits |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2 (async), asyncpg |
| Database | PostgreSQL 16 + `pgvector` + `halfvec`/HNSW where configured |
| AI | OpenAI (default: `gpt-4o-mini` chat, `text-embedding-3-large` embeddings) |
| Frontend | Next.js 16+, React 19+, TypeScript, Tailwind CSS v4 |
| CI | GitHub Actions — backend Ruff, Alembic, pytest; frontend ESLint / tests / build |

Hosting is documented for **Railway** (API + DB) and **Vercel** (web); see `docs/DEPLOYMENT.md` for overrides.

---

## Prerequisites

- **Python** 3.12+
- **Node** 18+ with **pnpm** (repo Makefile uses `pnpm`)
- **Docker** Desktop (recommended for local PostgreSQL via compose)
- **OpenAI API key** (for real chat/embeddings locally)
- PostgreSQL **16** with the **vector** extension if you skip Docker

---

## Quick start

```bash
# 1. Environment
cp .env.example .env
# Edit .env — set OPENAI_API_KEY, DATABASE_URL, JWT_SECRET for real use.

# 2. Backend
cd apps/api && pip install -r requirements.txt   # pinned deps for repeatable installs

# 3. Frontend
cd ../web && pnpm install

# 4. Postgres (from repo root)
make docker-up
make migrate
make seed

# 5. Dev servers — two terminals, from repo root
make dev-api    # http://localhost:8000  (Swagger: /docs)
make dev-web    # http://localhost:3000
```

If Postgres is down, API routes that need the DB respond with **`503`** and a hint to run **`make docker-up`** (see `apps/api/app/core/errors.py`).

---

## Makefile shortcuts

| Target | Purpose |
|--------|---------|
| `make dev-api` | Run FastAPI with reload |
| `make dev-web` | Run Next dev server |
| `make docker-up` / `docker-down` | Start/stop local Postgres (`infra/docker/docker-compose.yml`) |
| `make migrate` | `alembic upgrade head` |
| `make seed` | Seed admin (`apps/api/scripts/seed_admin.py`) |
| `make test-api` | Pytest excluding integration-heavy paths where `SKIP_INTEGRATION=1` |
| `make test-api-integration` | Full integration pytest (needs DB) |
| `make lint` | API Ruff + web ESLint |

---

## Documentation index

| File | Contents |
|------|----------|
| `docs/ARCHITECTURE.md` | System shape, layering, diagrams |
| `docs/PRODUCT_SPEC.md` | Product scope and personas |
| `docs/API_CONTRACT.md` | HTTP API contract |
| `docs/DATABASE_SCHEMA.md` | Tables, columns, constraints |
| `docs/AI_SYSTEM.md` | RAG, prompting, routing, safety |
| `docs/SECURITY.md` | Threat model baseline, JWT, secrets |
| `docs/DEPLOYMENT.md` | Railway / Vercel / Docker |
| `docs/TESTING.md` | Backend + frontend testing |
| `docs/plans/week-*.md` | Archived weekly delivery notes |

---

## Environment variables

The canonical list lives in **`.env.example`**. Highlights:

| Variable | Role |
|---------|------|
| `DATABASE_URL` | Async SQLAlchemy DSN (`postgresql+asyncpg://…`) |
| `OPENAI_API_KEY` | **Secret** — never commit or expose to the browser |
| `JWT_SECRET` | **Secret** — must not stay at the repo default in production |
| `CORS_ORIGINS` | Allowed browser origins (`http://localhost:3000`, prod domains) |
| `NEXT_PUBLIC_API_URL` | Browser-visible API base (safe — no secrets) |

Frontend code must **only** surface `NEXT_PUBLIC_*` variables to the bundle.

---

## Public repository hygiene

- **No secrets in git.** Use `.env` locally (gitignored) and platform secret managers in production.
- **`plan.md` at repo root is gitignored** — long-form playbook stays local-only.
- **Interview-preparation artifacts** matching `docs/KRYSTAL_STUDIO_INTERVIEW_PREP*` and `scripts/interview_md_to_pdf.py` are gitignored.
- **`krystal_dev_password` in compose / `.env.example`** is **local development only**. Change all credentials before any shared or production deployment.
- Prefer **credential rotation** (`JWT_SECRET`, DB passwords, API keys) when forking this repo publicly.

See also **`docs/SECURITY.md`**.

---

## Project layout

```
apps/api/       FastAPI backend, Alembic, pytest
apps/web/       Next.js app — public pages, chat widget, admin
docs/           Specs & decisions
infra/docker/   Local PostgreSQL Compose file
scripts/        Seeds, backups, utilities
```

---

## Testing

```bash
make test-api
make test-api-integration   # PostgreSQL required
cd apps/web && pnpm test && pnpm exec tsc --noEmit && pnpm lint
```

Integration tests (`apps/api/app/tests/integration/conftest.py`) use deterministic embedding stubs and documented **dev-only** defaults — override with `.env` for your machine.

---

## Contributing

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:` (prefer short subjects under 72 characters)
- Branch from `main` with small, reviewable changes
- All PRs should pass **`ci.yml`** (lint, migrations, pytest without live OpenAI, front build)

---

## License

Distributed under the **MIT License** — see [`LICENSE`](LICENSE).
