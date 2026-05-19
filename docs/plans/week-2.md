# Week 2 — Database, Auth, and Knowledge Management

> **Status:** COMPLETED
> **Depends on:** Week 1 completed
> **Blocks:** Week 3, Week 4

---

## Goal

Admin can log in, authenticate via JWT (access + refresh), and manage knowledge documents (CRUD). Database models and migrations are solid: pgvector self-contained in migrations, CHECK constraints, indexes including HNSW on embeddings. All admin APIs protected with role-based access. CI runs on PR and main.

---

## Review alignment (2026-05-13 CEO review)

This plan incorporates SELECTIVE EXPANSION decisions: refresh tokens, GitHub Actions CI (Week 2 scope), HNSW index on chunk embeddings, database CHECK constraints, `api_keys` and `audit_logs` tables, login rate limiting (in-memory), production JWT secret startup guard, password minimum length, pagination caps, knowledge status state machine, async/pytest-asyncio tests, `service_type` default `"general"`, response schemas with `model_config = ConfigDict(from_attributes=True)`, optional audit writes from admin mutations (minimal hooks), and feature-branch PR workflow (no direct push to `main`).

Deferred to **TODOS.md**: Redis-backed distributed rate limiting (P2), password reset flow (P3).

---

## Pre-Implementation Questions (ASK USER BEFORE STARTING)

1. What email and password do you want for the initial admin seed user? (Default: `admin@krystaltattoo.com` / auto-generated; seed passwords must meet minimum length below.)
2. Do you want multiple roles (owner/admin/staff) from the start, or just admin for MVP?
3. Should knowledge documents support multiple languages from the start? (Recommended: Yes)
4. What is the maximum knowledge document size you expect? (Helps with chunking config)

---

## Cross-cutting requirements (all tasks)

### Migrations

- First Alembic revision that introduces vectors MUST include `CREATE EXTENSION IF NOT EXISTS vector` so migrations work on a fresh DB (e.g. Railway), not only via Docker `init.sql`.
- Add PostgreSQL **CHECK** constraints matching enums/strings used in app code:
  - `users.role` IN (`owner`, `admin`, `staff`)
  - `knowledge_documents.status` IN (`draft`, `active`, `archived`)
  - `leads.status` IN (`new`, `contacted`, `consultation_booked`, `converted`, `closed`)
  - `conversations.status` IN (`active`, `ended`)
  - `messages.role` IN (`user`, `assistant`, `system`)
  - `ai_feedback.rating` BETWEEN 1 AND 5

### Indexes

Add B-tree (or appropriate) indexes for filtered/joined columns, including at minimum: `users.email`, `refresh_tokens.token_hash`, `refresh_tokens.user_id`, `knowledge_documents.status`, `knowledge_chunks.document_id`, `knowledge_chunks.language`, `knowledge_chunks.service_type`, foreign keys on leads/conversations/messages/analytics/feedback as needed, plus:

**HNSW on embeddings** (after chunks exist):

```sql
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw
ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

### Exceptions and HTTP mapping

Extend **`apps/api/app/core/errors.py`** with domain exceptions (e.g. `NotFoundError`, `ConflictError`, `InvalidCredentialsError`, `AccountInactiveError`, `TokenExpiredError`). Register handlers in **`apps/api/app/main.py`** mapping each to 401/403/404/409 as appropriate. Services raise domain exceptions; routes stay thin. Avoid bare `except Exception` swallowing.

### Startup guard

If `ENVIRONMENT=production` and `JWT_SECRET` equals the placeholder default (`change-me-in-production` from config), **fail fast at startup** with a clear error.

### Auth security

- **`LoginRequest.password`:** `Field(..., min_length=8)`.
- **Login endpoint:** in-memory rate limit (e.g. 5 attempts per minute per IP); return **429** with `Retry-After` when exceeded. Week 6 upgrades to Redis-backed limiting where needed (see TODOS.md).

### `require_role`

Implement in **`apps/api/app/api/deps.py`**: factory returning a FastAPI dependency that runs **after** `get_current_user`. Wrong role → **403 Forbidden**. Missing/invalid token → **401** (handled by `get_current_user`). Inactive users rejected in `get_current_user` → **401** or **403** per your chosen convention (document it once and test).

### Tests

- Use **`pytest-asyncio`** and **`async def`** for any test that `await`s DB or async services.
- Add integration test for **refresh token** expiry/revocation paths as applicable.
- Add tests for **knowledge status transitions** (see Task 2.6).
- Add optional smoke test or Makefile target: migration **upgrade → downgrade -1 → upgrade head**.

### Git workflow

Work on **`feature/week2-database-auth`** (or similar). Open a **PR** to `main`. Do **not** `git push origin main` until PR is merged.

---

## Tasks

### Task 2.1 — User Model and Migration

**What:** Create the `users` table with SQLAlchemy model and Alembic migration (CHECK + indexes as above).

**Files to create/modify:**

```
apps/api/app/db/models/user.py
apps/api/app/db/models/__init__.py  (add export)
apps/api/app/schemas/auth.py
apps/api/app/schemas/__init__.py  (add export)
```

**User model fields:**

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key, auto-generated |
| email | String(255) | Unique, not null, indexed |
| password_hash | String(255) | Not null |
| role | String(20) | Default: `admin`, CHECK: owner/admin/staff |
| is_active | Boolean | Default: true |
| created_at | DateTime(timezone=True) | Server default: now() |
| updated_at | DateTime(timezone=True) | On update: now() |

**Auth schemas:**

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
```

**Steps:**
1. Create `user.py` model
2. Export from `models/__init__.py`
3. Import in `base.py` so Alembic sees it
4. Generate migration: `alembic revision --autogenerate -m "add users table"`
5. Apply: `alembic upgrade head`

**Tests:**

```python
# apps/api/app/tests/unit/test_user_model.py — use @pytest.mark.asyncio and async def + await db_session.commit()
```

**Verification:**
```bash
cd apps/api && alembic upgrade head
# Check: \dt users in psql
```

---

### Task 2.2 — Password Hashing and JWT Auth

**What:** Implement password hashing, access JWT, refresh token persistence, validation helpers.

**Files to create/modify:**

```
apps/api/app/core/security.py  (update)
apps/api/app/api/deps.py  (update)
apps/api/app/db/models/refresh_token.py  (new — hashed refresh token storage)
```

**Requirements:**
- Use `passlib[bcrypt]` for password hashing
- Use `python-jose` for JWT access tokens
- `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`
- Refresh tokens: store **hash only** in DB (never raw token in logs); configurable expiry (env e.g. `REFRESH_TOKEN_EXPIRE_DAYS`)
- `get_current_user` → loads user from access token subject
- `require_role(*roles: str)` → dependency factory in `deps.py` as described above

**Constraints:**
- JWT secret from `JWT_SECRET`; expiry from `ACCESS_TOKEN_EXPIRE_MINUTES`
- Never log tokens, refresh tokens, or passwords

**Tests:** unit tests for hash/verify, access encode/decode, refresh token create/validate (mock DB as needed).

---

### Task 2.3 — Auth Endpoints

**What:** Login, refresh, and current-user endpoints with login rate limit.

**Files to create/modify:**

```
apps/api/app/api/v1/admin_auth.py
apps/api/app/api/v1/router.py  (register auth routes)
apps/api/app/core/rate_limit.py  (in-memory limiter for POST .../login — or minimal inline with tests)
```

**Endpoints:**

```
POST /api/v1/admin/auth/login    -> TokenResponse (access + refresh)
POST /api/v1/admin/auth/refresh  -> TokenResponse (rotate refresh token — issue new refresh + access)
GET  /api/v1/admin/me            -> UserResponse (protected)
```

**Flow for POST /login:** validate → lookup user → verify password → check `is_active` → issue access JWT → create refresh token row (hash) → return both.

**Flow for POST /refresh:** validate body → lookup refresh by hash → check expiry → check user still active → rotate refresh (invalidate old or replace — pick one strategy and test).

**Flow for GET /me:** Bearer access token → `get_current_user` → `UserResponse`.

**Tests:** integration tests for login success/failure, refresh success/expired, GET `/me` 401 without token, rate limit 429 on repeated login failures.

---

### Task 2.4 — Seed Admin Script

**What:** Script to seed initial admin user (password must satisfy `min_length=8`).

**Files:**

```
scripts/seed_admin.py
```

**Requirements:**
- Reads `DATABASE_URL` from env
- Creates owner user if not exists
- Email: `ADMIN_EMAIL` or default `admin@krystaltattoo.com`
- Password: `ADMIN_PASSWORD` or auto-generate (≥8 chars) and print once
- Idempotent

---

### Task 2.5 — Knowledge Document Model and Migration

**What:** Create `knowledge_documents` and `knowledge_chunks` with pgvector extension in migration chain, CHECK constraints, indexes, HNSW on `embedding`.

**Files:**

```
apps/api/app/db/models/knowledge.py
apps/api/app/schemas/knowledge.py
```

**knowledge_documents:** (unchanged intent; add CHECK on `status`)

**knowledge_chunks:**

| Column | Type | Notes |
|---|---|---|
| service_type | String(50) | **NOT NULL**, default **`general`**; CHECK tattoo/piercing/dreadlock/general |

**Schemas:** `KnowledgeDocumentCreate`, `KnowledgeDocumentUpdate`, `KnowledgeDocumentResponse`, `KnowledgeChunkResponse` with **`model_config = ConfigDict(from_attributes=True)`**.

**Steps:**
1. Ensure extension migration step exists before `Vector` columns
2. Create models + migration + HNSW index
3. Apply migration

---

### Task 2.6 — Knowledge Document CRUD Service

**What:** Service layer with explicit **status transition** rules.

**Allowed transitions:**
- `draft` → `active` (publish)
- `draft` → `archived` — **reject** (must activate first)
- `active` → `archived`
- `archived` → `active` (unarchive)

Raise domain error on illegal transition. Implement in `update_document` or dedicated method.

**Methods:** (same as before; enforce `list_documents` pagination — **defaults `skip=0`, `limit=20`, clamp `limit` to max `100`** at service or route layer.)

**Tests:** async tests for valid/invalid transitions.

---

### Task 2.7 — Knowledge Admin API Endpoints

**What:** CRUD + placeholder reindex; document query params **`skip`**, **`limit`** (max 100).

**Pagination:** `GET /api/v1/admin/knowledge?skip=0&limit=20&status=...`

**Optional:** after create/update/delete/reindex, append **`audit_logs`** row (user_id, action, entity_type, entity_id, changes_json) — keep handler thin; call small audit helper.

**Reindex:** Returns **202** with agreed JSON body until Week 3 wires ingestion.

---

### Task 2.8 — Additional Models and Migration (Foundation)

**What:** Create tables: **`refresh_tokens`**, **`api_keys`**, **`audit_logs`**, plus **`leads`**, **`conversations`**, **`messages`**, **`analytics_events`**, **`ai_feedback`**.

**Files (adjust as you split migrations):**

```
apps/api/app/db/models/refresh_token.py
apps/api/app/db/models/api_key.py
apps/api/app/db/models/audit_log.py
apps/api/app/db/models/lead.py
apps/api/app/db/models/conversation.py
apps/api/app/db/models/message.py
apps/api/app/db/models/analytics.py
apps/api/app/db/models/feedback.py
apps/api/app/schemas/lead.py
apps/api/app/schemas/chat.py
apps/api/app/schemas/analytics.py
```

**`api_keys` (minimal):** id, provider (text), key_encrypted or hashed secret reference, is_active, created_at, updated_at — align with docs/ARCHITECTURE.md future provider rotation (no need to wire UI this week).

**`audit_logs`:** id, user_id (FK users nullable if system), action, entity_type, entity_id (UUID), changes_json (nullable), created_at.

Follow **docs/ARCHITECTURE.md Section 6.3** for lead/chat/analytics/feedback columns + CHECKs for statuses/roles/rating.

**Verification:** `\dt` lists **11** core tables: users, refresh_tokens, api_keys, audit_logs, knowledge_documents, knowledge_chunks, leads, conversations, messages, analytics_events, ai_feedback.

---

### Task 2.9 — GitHub Actions CI

**What:** `.github/workflows/ci.yml` — on `push` and `pull_request` to `main`: backend install, ruff/pytest (unit + integration); frontend pnpm install, lint, `tsc`, build. Use paths or matrix as appropriate for monorepo.

**Note:** Matches scope moved from TODOS.md P2 into Week 2.

---

## Testing Checklist (Run After ALL Tasks Complete)

- [ ] All migrations apply cleanly: `alembic upgrade head`
- [ ] Rollback works: `alembic downgrade -1` then `alembic upgrade head` (or scripted smoke)
- [ ] **11** tables exist (see Task 2.8)
- [ ] `vector` extension exists via migration (verify on fresh DB)
- [ ] HNSW index exists on `knowledge_chunks.embedding`
- [ ] CHECK constraints reject invalid enum-like values (manual or test)
- [ ] `make seed` / seed admin runs; password meets min length
- [ ] Login returns access + refresh tokens; refresh returns new tokens
- [ ] Login rate limit returns **429** after threshold
- [ ] Production JWT placeholder rejected at startup when `ENVIRONMENT=production`
- [ ] GET `/api/v1/admin/me` works with access token; **401** without
- [ ] Knowledge CRUD + pagination caps behave correctly
- [ ] Knowledge status transition tests pass
- [ ] CI workflow passes on PR
- [ ] All unit tests pass: `cd apps/api && python -m pytest app/tests/unit/ -v`
- [ ] All integration tests pass: `cd apps/api && python -m pytest app/tests/integration/ -v`
- [ ] Lint passes: `make lint`

---

## Git Commit Strategy

Use a **feature branch** (e.g. `feature/week2-database-auth`), push branch, open **PR** to `main`.

```bash
git checkout -b feature/week2-database-auth

# After Task 2.1–2.2 (+ refresh_token model if merged here)
git add -A && git commit -m "feat(db): add users, refresh tokens, password hashing and JWT"

# After Task 2.3–2.4
git commit -m "feat(auth): login, refresh, rate limit, seed admin"

# After Task 2.5–2.7
git commit -m "feat(knowledge): documents, chunks, CRUD API, indexes and HNSW"

# After Task 2.8
git commit -m "feat(db): api_keys, audit_logs, leads, chats, analytics, feedback"

# After Task 2.9
git commit -m "ci: add GitHub Actions workflow for api and web"

git push -u origin feature/week2-database-auth
# Open PR → merge to main after review
```

---

## After Week 2 Completion

- [ ] Update docs/ARCHITECTURE.md checklist — mark Phase 2, 3, 4, 5 items as done
- [ ] Update this file's status to COMPLETED
- [ ] Proceed to `docs/plans/week-3.md`
