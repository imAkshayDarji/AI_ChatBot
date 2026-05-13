# Week 1 — Architecture, Planning, and Foundation

> **Status:** NOT STARTED
> **Dates:** Week 1
> **Depends on:** None
> **Blocks:** Week 2, Week 3, Week 4, Week 5, Week 6

---

## Goal

Project structure is stable, Cursor rules are active, backend/frontend run locally, database works.

## Configuration Decisions

| Decision | Value |
|---|---|
| AI Provider | OpenAI GPT-4o-mini (chat) |
| Embedding Model | OpenAI text-embedding-3-large |
| Python Version | 3.12 |
| Node.js Version | 20 LTS |
| Package Manager | pnpm |
| Studio Name | Krystal Tattoo Studio |
| Local PostgreSQL | Docker |
| Backend Hosting | Railway |
| Frontend Hosting | Vercel |
| Git Remote | https://github.com/imAkshayDarji/AI_ChatBot.git |

---

## Pre-Implementation Questions (ASK USER BEFORE STARTING)

1. What is the studio's official phone number? (Used in handoff messages, .env.example)
2. What is the studio's official Instagram URL? (Used in handoff messages, .env.example)
3. What is the studio's website URL? (Used for CORS, frontend config)
4. What is the studio's address/location? (Used in knowledge base, responses)
5. What are the studio's opening hours? (Used in knowledge base, responses)
6. Do you have a logo file you want to use in the chat widget?

---

## Tasks

### Task 1.1 — Documentation Foundation

**What:** Create all architecture and design documents.

**Files to create:**

```
docs/ARCHITECTURE.md
docs/PRODUCT_SPEC.md
docs/API_CONTRACT.md
docs/DATABASE_SCHEMA.md
docs/AI_SYSTEM.md
docs/SECURITY.md
docs/DEPLOYMENT.md
docs/TESTING.md
docs/DECISIONS/.gitkeep
```

**Constraints:**
- Each document must be derived from PLAN.md
- API_CONTRACT.md must list every endpoint from PLAN.md Section 9
- DATABASE_SCHEMA.md must cover all 8 core tables from PLAN.md Section 6
- AI_SYSTEM.md must cover provider abstraction, prompt builder, safety, RAG flow
- SECURITY.md must cover all MVP security requirements from PLAN.md Section 15
- Do NOT implement code in this task. Documentation only.

**Verification:**
- All 8 document files exist
- Each document is internally consistent
- Each document aligns with PLAN.md

---

### Task 1.2 — Cursor Rules

**What:** Create all Cursor rule files.

**Files to create:**

```
.cursor/rules/project.mdc
.cursor/rules/backend.mdc
.cursor/rules/frontend.mdc
.cursor/rules/database.mdc
.cursor/rules/ai-rag.mdc
.cursor/rules/security.mdc
```

**Content:** Use exact content from PLAN.md Section 13.1–13.6.

**Constraints:**
- Do not modify or invent rules beyond what PLAN.md specifies.
- These rules govern all future AI-generated code.

**Verification:**
- All 6 .mdc files exist with correct content
- Cursor picks them up (check in Cursor settings)

---

### Task 1.3 — Monorepo Structure

**What:** Create the full monorepo folder structure.

**Files to create:**

```
studio-ai-platform/
  apps/
    api/
      app/
        __init__.py
        main.py
        core/
          __init__.py
          config.py
          security.py
          logging.py
          errors.py
          rate_limit.py
        db/
          __init__.py
          session.py
          base.py
          models/
            __init__.py
          migrations/
        api/
          __init__.py
          deps.py
          v1/
            __init__.py
            router.py
            health.py
        schemas/
          __init__.py
          common.py
        services/
          __init__.py
          ai/
            __init__.py
            prompts/
              __init__.py
          rag/
            __init__.py
          chat/
            __init__.py
          leads/
            __init__.py
          analytics/
            __init__.py
          admin/
            __init__.py
        workers/
          __init__.py
        tests/
          __init__.py
          unit/
            __init__.py
          integration/
            __init__.py
          ai_eval/
            __init__.py
      alembic/
        versions/
        env.py
        alembic.ini
      requirements.txt
      Dockerfile
    web/
      (Next.js will generate this in Task 1.5)
  packages/
    shared/
      .gitkeep
  docs/
    (already created in Task 1.1)
  infra/
    docker/
      docker-compose.yml
    railway/
      .gitkeep
    vercel/
      .gitkeep
  scripts/
    seed_admin.py
    seed_knowledge.py
    backup_db.sh
  .github/
    workflows/
      .gitkeep
  .cursor/
    rules/
      (already created in Task 1.2)
  .env.example
  .gitignore
  Makefile
  README.md
```

**Note:** The project root is currently `/Users/akshaydarji/myProjects/KrystalStudio/`. The monorepo structure will be created inside this directory. We will reorganize so that `plan.md` and `docs/` sit at the monorepo root.

**Constraints:**
- Follow PLAN.md Section 4.1 exactly
- All `__init__.py` files for Python packages
- `.gitkeep` for empty directories

**Verification:**
- `tree` command shows correct structure
- No missing directories

---

### Task 1.4 — FastAPI Backend Skeleton

**What:** Create a minimal FastAPI app that starts and responds to health check.

**Files to modify:**

```
apps/api/app/main.py
apps/api/app/core/config.py
apps/api/app/core/errors.py
apps/api/app/core/logging.py
apps/api/app/api/v1/router.py
apps/api/app/api/v1/health.py
apps/api/app/api/deps.py
apps/api/requirements.txt
apps/api/Dockerfile
.env.example
```

**Requirements:**
- FastAPI app with CORS middleware (configurable origins)
- `/api/v1/health` endpoint returns `{"status": "ok", "version": "1.0.0"}`
- Pydantic v2 settings class in `config.py` reading from env vars
- Global exception handlers in `errors.py`
- Structured logging setup in `logging.py`
- `requirements.txt` with pinned versions: fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic, pydantic-settings, python-jose, passlib, httpx, openai, pgvector
- Dockerfile using python:3.12-slim

**Constraints:**
- Do NOT implement business logic
- Do NOT connect to database yet
- Do NOT implement auth yet
- Route handlers must be thin
- Use async def for all endpoints

**Verification:**
```bash
cd apps/api && pip install -r requirements.txt
uvicorn app.main:app --reload
curl http://localhost:8000/api/v1/health  # returns {"status": "ok", "version": "1.0.0"}
```

**Tests:**
```python
# apps/api/app/tests/unit/test_health.py
def test_health_endpoint_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

### Task 1.5 — Next.js Frontend Skeleton

**What:** Create a minimal Next.js app that loads.

**Commands:**

```bash
cd apps/
pnpm create next-app web --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"
```

**After scaffold, modify/create:**

```
apps/web/.env.example
apps/web/.env.local (gitignored)
apps/web/lib/api.ts  (empty API client placeholder)
apps/web/types/api.ts (empty types placeholder)
apps/web/components/ui/.gitkeep
apps/web/components/chat/.gitkeep
apps/web/components/admin/.gitkeep
apps/web/app/page.tsx (landing page with "Krystal Tattoo Studio" heading)
apps/web/app/admin/ (admin route group placeholder)
```

**Requirements:**
- TypeScript strict mode
- Tailwind CSS v4 configured
- shadcn/ui initialized (`pnpm dlx shadcn@latest init`)
- API client placeholder in `lib/api.ts` with `NEXT_PUBLIC_API_URL` base URL
- Mobile-responsive layout
- `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.example`
- `NEXT_PUBLIC_STUDIO_NAME="Krystal Tattoo Studio"` in `.env.example`

**Constraints:**
- Do NOT build chat widget yet
- Do NOT build admin pages yet
- Do NOT hardcode backend URLs (use env vars)
- Do NOT add shadcn/ui components yet (just init)

**Verification:**
```bash
cd apps/web && pnpm dev
# Opens http://localhost:3000 with "Krystal Tattoo Studio" heading
```

---

### Task 1.6 — Docker Compose for Local PostgreSQL

**What:** Create docker-compose.yml for local PostgreSQL + pgvector.

**Files to create:**

```
infra/docker/docker-compose.yml
```

**docker-compose.yml contents:**

```yaml
version: "3.9"
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: krystal_studio_db
    environment:
      POSTGRES_USER: krystal
      POSTGRES_PASSWORD: krystal_dev_password
      POSTGRES_DB: krystal_studio
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  postgres_data:
```

**Also create:**

```
infra/docker/init.sql
```

With:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Constraints:**
- Use pgvector/pgvector:pg16 image (not :latest)
- Password is dev-only, never used in production
- Document connection string in `.env.example`

**Verification:**
```bash
cd infra/docker && docker-compose up -d
docker exec -it krystal_studio_db psql -U krystal -d krystal_studio -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
# Should show vector extension installed
docker-compose down
```

---

### Task 1.7 — Alembic Configuration

**What:** Set up Alembic for database migrations.

**Files to modify:**

```
apps/api/alembic/env.py
apps/api/alembic.ini
apps/api/app/db/session.py
apps/api/app/db/base.py
```

**Requirements:**
- Alembic configured for async SQLAlchemy
- Database URL from environment variable `DATABASE_URL`
- `session.py` provides async engine and session factory
- `base.py` provides declarative base for models
- Connection string: `postgresql+asyncpg://krystal:krystal_dev_password@localhost:5432/krystal_studio`

**Constraints:**
- Do NOT create models yet
- Do NOT run migrations yet
- Use async SQLAlchemy patterns

**Verification:**
```bash
cd apps/api && alembic current
# Should show "No revision yet" without errors
```

---

### Task 1.8 — Makefile

**What:** Create a Makefile for common development commands.

**Files to create:**

```
Makefile
```

**Commands to include:**

```makefile
.PHONY: dev-api dev-web test-api lint migrate seed docker-up docker-down

# Backend
dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

test-api:
	cd apps/api && python -m pytest app/tests/ -v

lint:
	cd apps/api && python -m ruff check app/ && cd ../../apps/web && pnpm lint

migrate:
	cd apps/api && alembic upgrade head

seed:
	cd apps/api && python scripts/seed_admin.py

# Frontend
dev-web:
	cd apps/web && pnpm dev

# Docker
docker-up:
	cd infra/docker && docker-compose up -d

docker-down:
	cd infra/docker && docker-compose down
```

**Verification:**
```bash
make docker-up   # starts PostgreSQL
make dev-api     # starts backend (in another terminal)
make dev-web     # starts frontend (in another terminal)
```

---

### Task 1.9 — .gitignore and .env.example

**What:** Create proper gitignore and environment template.

**Files to create:**

```
.gitignore
.env.example
```

**.gitignore must include:**

```
__pycache__/
*.pyc
.env
.env.local
node_modules/
.next/
.pytest_cache/
.ruff_cache/
*.egg-info/
dist/
build/
.DS_Store
*.swp
venv/
.venv/
postgres_data/
```

**.env.example must include:**

```env
# Backend
DATABASE_URL=postgresql+asyncpg://krystal:krystal_dev_password@localhost:5432/krystal_studio
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
CORS_ORIGINS=http://localhost:3000
STUDIO_PHONE=+91-YOUR-PHONE
STUDIO_INSTAGRAM_URL=https://instagram.com/your-studio
STUDIO_NAME=Krystal Tattoo Studio
ENVIRONMENT=development

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STUDIO_NAME=Krystal Tattoo Studio
```

---

## Testing Checklist (Run After ALL Tasks Complete)

- [ ] All docs created in `docs/`
- [ ] All Cursor rules created in `.cursor/rules/`
- [ ] `make docker-up` starts PostgreSQL with pgvector
- [ ] `make dev-api` starts FastAPI on port 8000
- [ ] `curl http://localhost:8000/api/v1/health` returns `{"status": "ok"}`
- [ ] `make dev-web` starts Next.js on port 3000
- [ ] `http://localhost:3000` shows "Krystal Tattoo Studio"
- [ ] `cd apps/api && alembic current` runs without error
- [ ] `cd apps/api && python -m pytest` passes (health test)
- [ ] `make lint` runs without errors
- [ ] `.env.example` exists, no `.env` committed
- [ ] `.gitignore` covers all sensitive files

---

## Git Commit Strategy

After completing ALL tasks and passing the testing checklist:

```bash
git init
git add .
git commit -m "feat: initialize monorepo with FastAPI backend, Next.js frontend, and project docs"
git branch -M main
git remote add origin https://github.com/imAkshayDarji/AI_ChatBot.git
git push -u origin main
```

---

## After Week 1 Completion

- [ ] Update PLAN.md Section 22 (checklist) — mark Phase 0 and Phase 1 items as done
- [ ] Update this file's status to COMPLETED
- [ ] Proceed to `docs/plans/week-2.md`
