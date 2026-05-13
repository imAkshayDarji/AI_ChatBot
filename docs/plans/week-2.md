# Week 2 — Database, Auth, and Knowledge Management

> **Status:** NOT STARTED
> **Depends on:** Week 1 completed
> **Blocks:** Week 3, Week 4

---

## Goal

Admin can log in, authenticate via JWT, and manage knowledge documents (CRUD). Database models and migrations are solid. All protected with role-based access.

---

## Pre-Implementation Questions (ASK USER BEFORE STARTING)

1. What email and password do you want for the initial admin seed user? (Default: `admin@krystaltattoo.com` / auto-generated)
2. Do you want multiple roles (owner/admin/staff) from the start, or just admin for MVP?
3. Should knowledge documents support multiple languages from the start? (Recommended: Yes)
4. What is the maximum knowledge document size you expect? (Helps with chunking config)

---

## Tasks

### Task 2.1 — User Model and Migration

**What:** Create the `users` table with SQLAlchemy model and Alembic migration.

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
| role | String(20) | Default: "admin", check: owner/admin/staff |
| is_active | Boolean | Default: true |
| created_at | DateTime(timezone=True) | Server default: now() |
| updated_at | DateTime(timezone=True) | On update: now() |

**Auth schemas:**

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
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
# apps/api/app/tests/unit/test_user_model.py
def test_user_model_create(db_session):
    user = User(email="test@test.com", password_hash="hash", role="admin")
    db_session.add(user)
    await db_session.commit()
    assert user.id is not None
    assert user.role == "admin"

def test_user_email_unique(db_session):
    # creating two users with same email should fail
    ...
```

**Verification:**
```bash
cd apps/api && alembic upgrade head
# Check: \dt users in psql
```

---

### Task 2.2 — Password Hashing and JWT Auth

**What:** Implement password hashing and JWT token generation/validation.

**Files to create/modify:**

```
apps/api/app/core/security.py  (update)
apps/api/app/api/deps.py  (update)
```

**Requirements:**
- Use `passlib[bcrypt]` for password hashing
- Use `python-jose` for JWT
- `hash_password(plain: str) -> str`
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(data: dict, expires_delta: timedelta) -> str`
- `get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User`
- `require_role(*roles: str) -> Dependency` that checks `current_user.role in roles`

**Constraints:**
- JWT secret from env var `JWT_SECRET`
- Token expiry from env var `ACCESS_TOKEN_EXPIRE_MINUTES`
- Never log tokens or passwords

**Tests:**

```python
# apps/api/app/tests/unit/test_security.py
def test_hash_and_verify_password():
    hashed = hash_password("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)

def test_create_and_decode_token():
    token = create_access_token({"sub": "user_id"})
    payload = decode_token(token)
    assert payload["sub"] == "user_id"
```

---

### Task 2.3 — Auth Endpoints

**What:** Create login endpoint and current-user endpoint.

**Files to create/modify:**

```
apps/api/app/api/v1/admin_auth.py
apps/api/app/api/v1/router.py  (register auth routes)
```

**Endpoints:**

```
POST /api/v1/admin/auth/login   -> TokenResponse
GET  /api/v1/admin/me           -> UserResponse (protected)
```

**Flow for POST /login:**
1. Validate email/password via schema
2. Look up user by email
3. Verify password
4. Check `is_active`
5. Create JWT
6. Return token

**Flow for GET /me:**
1. Extract token from Authorization header
2. Validate token via `get_current_user` dependency
3. Return user data

**Tests:**

```python
# apps/api/app/tests/integration/test_auth.py
def test_login_success(client, admin_user):
    response = client.post("/api/v1/admin/auth/login", json={
        "email": "admin@krystaltattoo.com",
        "password": "test_password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/admin/auth/login", json={
        "email": "admin@krystaltattoo.com",
        "password": "wrong"
    })
    assert response.status_code == 401

def test_me_with_valid_token(client, admin_token):
    response = client.get("/api/v1/admin/me", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "admin@krystaltattoo.com"

def test_me_without_token(client):
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401

def test_me_role_check(client, staff_token):
    # If staff tries admin-only endpoint, should get 403
    ...
```

---

### Task 2.4 — Seed Admin Script

**What:** Create script to seed initial admin user.

**Files to create:**

```
scripts/seed_admin.py
```

**Requirements:**
- Reads `DATABASE_URL` from env
- Creates admin user if not exists
- Email: from env `ADMIN_EMAIL` or default `admin@krystaltattoo.com`
- Password: from env `ADMIN_PASSWORD` or auto-generate and print
- Role: "owner"
- Idempotent (safe to run multiple times)

**Verification:**
```bash
cd apps/api && python ../../scripts/seed_admin.py
# Should print: "Admin user created: admin@krystaltattoo.com with password: xxxxx"
# Running again should print: "Admin user already exists"
```

---

### Task 2.5 — Knowledge Document Model and Migration

**What:** Create `knowledge_documents` and `knowledge_chunks` tables.

**Files to create/modify:**

```
apps/api/app/db/models/knowledge.py
apps/api/app/schemas/knowledge.py
```

**knowledge_documents fields:**

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| title | String(500) | Not null |
| source_type | String(50) | "manual", "website", "faq", "pdf", "instagram" |
| source_url | String(1000) | Nullable |
| language | String(10) | Default: "en" |
| content | Text | Not null |
| status | String(20) | "draft", "active", "archived" — default: "draft" |
| metadata_json | JSON | Nullable |
| created_at | DateTime(tz=True) | |
| updated_at | DateTime(tz=True) | |

**knowledge_chunks fields:**

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| document_id | UUID | FK -> knowledge_documents.id, ON DELETE CASCADE |
| chunk_text | Text | Not null |
| chunk_index | Integer | Not null |
| service_type | String(50) | Nullable — "tattoo", "piercing", "dreadlock", "general" |
| language | String(10) | Default: "en" |
| embedding | Vector(3072) | Nullable initially (filled by embedding service) |
| created_at | DateTime(tz=True) | |

**Note:** `Vector(3072)` matches text-embedding-3-large output dimension.

**Steps:**
1. Create models
2. Generate migration
3. Apply migration
4. Create schemas: `KnowledgeDocumentCreate`, `KnowledgeDocumentUpdate`, `KnowledgeDocumentResponse`, `KnowledgeChunkResponse`

**Tests:**

```python
# apps/api/app/tests/unit/test_knowledge_model.py
def test_create_knowledge_document(db_session):
    doc = KnowledgeDocument(title="Tattoo Pricing", source_type="manual", content="...")
    ...
    assert doc.status == "draft"

def test_document_chunk_relationship(db_session):
    doc = KnowledgeDocument(...)
    chunk = KnowledgeChunk(document_id=doc.id, chunk_text="...", chunk_index=0)
    ...
    assert chunk.document_id == doc.id
```

**Verification:**
```bash
cd apps/api && alembic upgrade head
# psql: \dt should show knowledge_documents and knowledge_chunks
```

---

### Task 2.6 — Knowledge Document CRUD Service

**What:** Create service layer for knowledge document operations.

**Files to create:**

```
apps/api/app/services/knowledge/service.py
```

**Methods:**

```python
async def create_document(db: AsyncSession, data: KnowledgeDocumentCreate) -> KnowledgeDocument
async def get_document(db: AsyncSession, document_id: UUID) -> KnowledgeDocument | None
async def list_documents(db: AsyncSession, skip: int, limit: int, status: str | None) -> list[KnowledgeDocument]
async def update_document(db: AsyncSession, document_id: UUID, data: KnowledgeDocumentUpdate) -> KnowledgeDocument
async def delete_document(db: AsyncSession, document_id: UUID) -> bool
async def count_documents(db: AsyncSession, status: str | None) -> int
```

**Constraints:**
- Business logic only, no HTTP concerns
- Use async SQLAlchemy
- Return domain models, not Pydantic schemas
- Raise specific exceptions (NotFound, Conflict)

**Tests:**

```python
# apps/api/app/tests/unit/test_knowledge_service.py
def test_create_document(db_session):
    doc = await create_document(db_session, KnowledgeDocumentCreate(
        title="Test", source_type="manual", content="Hello world"
    ))
    assert doc.id is not None
    assert doc.status == "draft"

def test_list_documents_with_status_filter(db_session):
    ...
```

---

### Task 2.7 — Knowledge Admin API Endpoints

**What:** Create admin-only CRUD endpoints for knowledge documents.

**Files to create/modify:**

```
apps/api/app/api/v1/admin_knowledge.py
apps/api/app/api/v1/router.py  (register knowledge routes)
```

**Endpoints:**

```
GET    /api/v1/admin/knowledge                     -> PaginatedResponse[KnowledgeDocumentResponse]
POST   /api/v1/admin/knowledge                     -> KnowledgeDocumentResponse
GET    /api/v1/admin/knowledge/{document_id}       -> KnowledgeDocumentResponse
PATCH  /api/v1/admin/knowledge/{document_id}       -> KnowledgeDocumentResponse
DELETE /api/v1/admin/knowledge/{document_id}       -> 204 No Content
POST   /api/v1/admin/knowledge/{document_id}/reindex -> 202 Accepted (placeholder)
```

**All endpoints require:** `get_current_user` dependency (authenticated admin).

**Reindex endpoint:** Returns 202 with `{"message": "Reindex queued"}` — actual implementation in Week 3.

**Tests:**

```python
# apps/api/app/tests/integration/test_knowledge_api.py
def test_admin_create_document(client, admin_token):
    response = client.post("/api/v1/admin/knowledge",
        headers=auth_header(admin_token),
        json={"title": "Tattoo Pricing", "source_type": "manual", "content": "..."}
    )
    assert response.status_code == 201

def test_admin_update_document(client, admin_token, sample_document):
    response = client.patch(f"/api/v1/admin/knowledge/{sample_document.id}",
        headers=auth_header(admin_token),
        json={"content": "Updated content"}
    )
    assert response.status_code == 200

def test_unauthenticated_create_rejected(client):
    response = client.post("/api/v1/admin/knowledge", json={...})
    assert response.status_code == 401

def test_invalid_document_rejected(client, admin_token):
    response = client.post("/api/v1/admin/knowledge",
        headers=auth_header(admin_token),
        json={"title": ""}  # missing required fields
    )
    assert response.status_code == 422

def test_delete_document(client, admin_token, sample_document):
    response = client.delete(f"/api/v1/admin/knowledge/{sample_document.id}",
        headers=auth_header(admin_token))
    assert response.status_code == 204
```

---

### Task 2.8 — Leads Model and Migration (Early Foundation)

**What:** Create `leads`, `conversations`, `messages`, `analytics_events`, `ai_feedback` tables. These are needed as foundation for later weeks.

**Files to create:**

```
apps/api/app/db/models/lead.py
apps/api/app/db/models/conversation.py
apps/api/app/db/models/message.py
apps/api/app/db/models/analytics.py
apps/api/app/db/models/feedback.py
apps/api/app/schemas/lead.py
apps/api/app/schemas/chat.py
apps/api/app/schemas/analytics.py
```

**Follow exact schema from PLAN.md Section 6.3.**

**Key fields to include:**

**leads:** id, name, email, phone, preferred_language, service_interest, budget_range, placement, style_preference, notes, status (new/contacted/consultation_booked/converted/closed), source, created_at, updated_at

**conversations:** id, session_id, lead_id (nullable FK), language, status (active/ended), summary, created_at, updated_at

**messages:** id, conversation_id (FK), role (user/assistant/system), content, intent, confidence, metadata_json, created_at

**analytics_events:** id, conversation_id (nullable FK), event_type, event_data (JSON), created_at

**ai_feedback:** id, message_id (FK), rating (1-5), comment, created_at

**Steps:**
1. Create all 5 models
2. Generate single migration: `alembic revision --autogenerate -m "add leads conversations messages analytics feedback"`
3. Apply migration

**Tests:**

```python
# apps/api/app/tests/unit/test_models.py
def test_create_lead(db_session): ...
def test_create_conversation(db_session): ...
def test_create_message(db_session): ...
def test_lead_status_values(db_session): ...
def test_conversation_message_relationship(db_session): ...
```

**Verification:**
```bash
cd apps/api && alembic upgrade head
# psql: \dt should show all 8 tables
# users, leads, conversations, messages, knowledge_documents, knowledge_chunks, analytics_events, ai_feedback
```

---

## Testing Checklist (Run After ALL Tasks Complete)

- [ ] All migrations apply cleanly: `alembic upgrade head`
- [ ] Rollback works: `alembic downgrade -1` then `alembic upgrade head`
- [ ] All 8 tables exist in database
- [ ] pgvector extension is active
- [ ] Admin seed script runs: `make seed`
- [ ] Admin login returns JWT: `POST /api/v1/admin/auth/login`
- [ ] GET /api/v1/admin/me works with valid token
- [ ] GET /api/v1/admin/me fails without token (401)
- [ ] Admin can create knowledge document
- [ ] Admin can list knowledge documents
- [ ] Admin can update knowledge document
- [ ] Admin can delete knowledge document
- [ ] Unauthenticated requests to admin endpoints return 401
- [ ] All unit tests pass: `cd apps/api && python -m pytest app/tests/unit/ -v`
- [ ] All integration tests pass: `cd apps/api && python -m pytest app/tests/integration/ -v`
- [ ] Lint passes: `make lint`

---

## Git Commit Strategy

```bash
# After Task 2.1-2.2
git add -A && git commit -m "feat(db): add user model, password hashing, and JWT auth"

# After Task 2.3-2.4
git add -A && git commit -m "feat(auth): add login endpoint and admin seed script"

# After Task 2.5-2.7
git add -A && git commit -m "feat(knowledge): add knowledge document CRUD with admin API"

# After Task 2.8
git add -A && git commit -m "feat(db): add leads, conversations, messages, analytics, feedback models"

# Push all
git push origin main
```

---

## After Week 2 Completion

- [ ] Update PLAN.md checklist — mark Phase 2, 3, 4, 5 items as done
- [ ] Update this file's status to COMPLETED
- [ ] Proceed to `docs/plans/week-3.md`
