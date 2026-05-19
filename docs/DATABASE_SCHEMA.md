# Database Schema — Krystal Studio AI Chatbot

> **Source of truth:** This document defines the complete database schema for the Krystal Studio AI Chatbot platform. All migrations and models must follow this schema exactly. Read README.md and docs/ARCHITECTURE.md before modifying this file.

---

## 1. General Rules

### 1.1 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Table names | snake_case, plural | `users`, `leads`, `knowledge_chunks` |
| Column names | snake_case | `created_at`, `service_interest` |
| Primary keys | `id` (UUID) | `id UUID PRIMARY KEY` |
| Foreign keys | `{entity}_id` | `lead_id`, `conversation_id`, `document_id` |
| Timestamps | `created_at`, `updated_at` with `timestamptz` | |
| JSON columns | `metadata_json` or `event_data` | |

### 1.2 Universal Columns

Every table includes:

- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Most tables also include:

- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 1.3 pgvector Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This must run before creating the `knowledge_chunks` table.

---

## 2. Tables

### 2.1 users

Stores admin and staff accounts for the admin dashboard.

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'staff',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT users_role_check CHECK (role IN ('owner', 'admin', 'staff'))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `email` | TEXT | No | — | Unique email address |
| `password_hash` | TEXT | No | — | Bcrypt password hash |
| `role` | TEXT | No | `'staff'` | User role: `owner`, `admin`, or `staff` |
| `created_at` | TIMESTAMPTZ | No | `now()` | Account creation time |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Last update time |

**Constraints:**
- `users_role_check` — `role` must be one of `owner`, `admin`, `staff`
- `users_email_key` — `email` must be unique

**Indexes:**
```sql
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
```

---

### 2.2 leads

Stores customer enquiries captured through the chat widget.

```sql
CREATE TABLE leads (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT,
    email               TEXT,
    phone               TEXT,
    preferred_language  TEXT DEFAULT 'en',
    service_interest    TEXT,
    budget_range        TEXT,
    placement           TEXT,
    style_preference    TEXT,
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'new',
    source              TEXT DEFAULT 'chat',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT leads_status_check CHECK (status IN ('new', 'contacted', 'consultation_booked', 'converted', 'closed'))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `name` | TEXT | Yes | — | Customer name |
| `email` | TEXT | Yes | — | Customer email |
| `phone` | TEXT | Yes | — | Customer phone number |
| `preferred_language` | TEXT | Yes | `'en'` | Preferred language code |
| `service_interest` | TEXT | Yes | — | Service category (`tattoo`, `piercing`, `dreadlock`) |
| `budget_range` | TEXT | Yes | — | Customer's stated budget |
| `placement` | TEXT | Yes | — | Desired body placement |
| `style_preference` | TEXT | Yes | — | Preferred style |
| `notes` | TEXT | Yes | — | Additional notes from customer or admin |
| `status` | TEXT | No | `'new'` | Lead lifecycle status |
| `source` | TEXT | Yes | `'chat'` | How the lead was captured |
| `created_at` | TIMESTAMPTZ | No | `now()` | Lead creation time |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Last update time |

**Constraints:**
- `leads_status_check` — `status` must be one of `new`, `contacted`, `consultation_booked`, `converted`, `closed`

**Indexes:**
```sql
CREATE INDEX idx_leads_status ON leads (status);
CREATE INDEX idx_leads_service_interest ON leads (service_interest);
CREATE INDEX idx_leads_created_at ON leads (created_at DESC);
CREATE INDEX idx_leads_source ON leads (source);
```

---

### 2.3 conversations

Stores chat sessions between visitors and the AI chatbot.

```sql
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  TEXT UNIQUE NOT NULL,
    lead_id     UUID REFERENCES leads(id) ON DELETE SET NULL,
    language    TEXT DEFAULT 'en',
    status      TEXT NOT NULL DEFAULT 'active',
    summary     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT conversations_status_check CHECK (status IN ('active', 'ended', 'handoff'))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `session_id` | TEXT | No | — | Unique session identifier (from frontend) |
| `lead_id` | UUID | Yes | — | FK to `leads.id` if a lead was captured |
| `language` | TEXT | Yes | `'en'` | Conversation language code |
| `status` | TEXT | No | `'active'` | Conversation state |
| `summary` | TEXT | Yes | — | Auto-generated or manual conversation summary |
| `created_at` | TIMESTAMPTZ | No | `now()` | Conversation start time |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Last activity time |

**Constraints:**
- `conversations_session_id_key` — `session_id` must be unique
- `conversations_status_check` — `status` must be one of `active`, `ended`, `handoff`
- `conversations_lead_id_fkey` — `lead_id` references `leads(id)` with `ON DELETE SET NULL`

**Indexes:**
```sql
CREATE INDEX idx_conversations_session_id ON conversations (session_id);
CREATE INDEX idx_conversations_lead_id ON conversations (lead_id);
CREATE INDEX idx_conversations_status ON conversations (status);
CREATE INDEX idx_conversations_language ON conversations (language);
CREATE INDEX idx_conversations_created_at ON conversations (created_at DESC);
```

---

### 2.4 messages

Stores individual chat messages within conversations.

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    intent          TEXT,
    confidence      FLOAT,
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `conversation_id` | UUID | No | — | FK to `conversations.id` |
| `role` | TEXT | No | — | Message sender: `user`, `assistant`, or `system` |
| `content` | TEXT | No | — | Message text content |
| `intent` | TEXT | Yes | — | Classified intent (e.g., `pricing_guidance`, `aftercare`) |
| `confidence` | FLOAT | Yes | — | AI confidence score (0.0–1.0) |
| `metadata_json` | JSONB | Yes | — | Additional metadata (sources, handoff reason, model used, tokens) |
| `created_at` | TIMESTAMPTZ | No | `now()` | Message timestamp |

**Constraints:**
- `messages_role_check` — `role` must be one of `user`, `assistant`, `system`
- `messages_conversation_id_fkey` — `conversation_id` references `conversations(id)` with `ON DELETE CASCADE`

**Indexes:**
```sql
CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX idx_messages_role ON messages (role);
CREATE INDEX idx_messages_intent ON messages (intent);
CREATE INDEX idx_messages_created_at ON messages (created_at);
CREATE INDEX idx_messages_conversation_created ON messages (conversation_id, created_at);
```

**metadata_json examples:**

Assistant message metadata:
```json
{
  "sources": [
    {"document_title": "Tattoo Pricing Guide", "chunk_id": "uuid"}
  ],
  "model": "gpt-4o-mini",
  "tokens_in": 450,
  "tokens_out": 120,
  "handoff": false,
  "handoff_reason": null,
  "lead_capture_suggested": true
}
```

---

### 2.5 knowledge_documents

Stores raw knowledge content for the RAG system.

```sql
CREATE TABLE knowledge_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    source_url      TEXT,
    language        TEXT DEFAULT 'en',
    content         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT knowledge_documents_source_type_check CHECK (source_type IN ('manual', 'website', 'pdf', 'faq'))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `title` | TEXT | No | — | Document title |
| `source_type` | TEXT | No | — | How the content was sourced: `manual`, `website`, `pdf`, `faq` |
| `source_url` | TEXT | Yes | — | URL if sourced from a website |
| `language` | TEXT | Yes | `'en'` | Document language code |
| `content` | TEXT | No | — | Full document text content |
| `status` | TEXT | No | `'active'` | Document status: `active`, `draft`, `archived` |
| `metadata_json` | JSONB | Yes | — | Additional metadata (service_type, category, chunk_count) |
| `created_at` | TIMESTAMPTZ | No | `now()` | Creation time |
| `updated_at` | TIMESTAMPTZ | No | `now()` | Last update time |

**Constraints:**
- `knowledge_documents_source_type_check` — `source_type` must be one of `manual`, `website`, `pdf`, `faq`

**Indexes:**
```sql
CREATE INDEX idx_knowledge_documents_status ON knowledge_documents (status);
CREATE INDEX idx_knowledge_documents_language ON knowledge_documents (language);
CREATE INDEX idx_knowledge_documents_source_type ON knowledge_documents (source_type);
CREATE INDEX idx_knowledge_documents_updated_at ON knowledge_documents (updated_at DESC);
```

---

### 2.6 knowledge_chunks

Stores vector-searchable text chunks derived from knowledge documents.

```sql
CREATE TABLE knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_text      TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    service_type    TEXT,
    language        TEXT DEFAULT 'en',
    embedding       VECTOR(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `document_id` | UUID | No | — | FK to `knowledge_documents.id` |
| `chunk_text` | TEXT | No | — | The text chunk content |
| `chunk_index` | INTEGER | No | — | Position of this chunk within the parent document (0-based) |
| `service_type` | TEXT | Yes | — | Service category: `tattoo`, `piercing`, `dreadlock`, or `general` |
| `language` | TEXT | Yes | `'en'` | Chunk language code |
| `embedding` | VECTOR(1536) | Yes | — | OpenAI text-embedding-3-large vector (1536 dimensions) |
| `created_at` | TIMESTAMPTZ | No | `now()` | Chunk creation time |

**Constraints:**
- `knowledge_chunks_document_id_fkey` — `document_id` references `knowledge_documents(id)` with `ON DELETE CASCADE`

**Indexes:**
```sql
CREATE INDEX idx_knowledge_chunks_document_id ON knowledge_chunks (document_id);
CREATE INDEX idx_knowledge_chunks_service_type ON knowledge_chunks (service_type);
CREATE INDEX idx_knowledge_chunks_language ON knowledge_chunks (language);

-- HNSW index for approximate nearest neighbor vector search
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**HNSW index parameters:**
- `m = 16` — Maximum number of connections per node in the graph
- `ef_construction = 64` — Size of the dynamic candidate list during construction
- `vector_cosine_ops` — Uses cosine distance for similarity search

**Vector search query pattern:**
```sql
SELECT id, chunk_text, document_id, service_type, language,
       1 - (embedding <=> $1::vector) AS similarity
FROM knowledge_chunks
WHERE language = $2
  AND service_type = $3
ORDER BY embedding <=> $1::vector
LIMIT $4;
```

---

### 2.7 analytics_events

Stores raw analytics events for tracking chatbot usage and behavior.

```sql
CREATE TABLE analytics_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL,
    event_data      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `conversation_id` | UUID | Yes | — | FK to `conversations.id` for event correlation |
| `event_type` | TEXT | No | — | Event type identifier |
| `event_data` | JSONB | Yes | — | Flexible event payload |
| `created_at` | TIMESTAMPTZ | No | `now()` | Event timestamp |

**Tracked event types:**

| Event Type | Description | event_data example |
|------------|-------------|-------------------|
| `chat_started` | New conversation started | `{"language": "en"}` |
| `language_selected` | User selected a language | `{"language": "hi"}` |
| `message_sent` | User sent a message | `{"message_length": 42}` |
| `assistant_response` | Chatbot responded | `{"intent": "pricing", "confidence": 0.87}` |
| `lead_capture_prompted` | Lead form suggested | `{"conversation_id": "uuid"}` |
| `lead_created` | Lead captured | `{"lead_id": "uuid", "service": "tattoo"}` |
| `handoff_triggered` | Handed off to human | `{"reason": "low_confidence"}` |
| `rag_no_result` | No relevant knowledge found | `{"query": "user message"}` |
| `feedback_positive` | User gave thumbs up | `{"message_id": "uuid"}` |
| `feedback_negative` | User gave thumbs down | `{"message_id": "uuid", "comment": "..."}` |

**Indexes:**
```sql
CREATE INDEX idx_analytics_events_conversation_id ON analytics_events (conversation_id);
CREATE INDEX idx_analytics_events_event_type ON analytics_events (event_type);
CREATE INDEX idx_analytics_events_created_at ON analytics_events (created_at DESC);
CREATE INDEX idx_analytics_events_type_created ON analytics_events (event_type, created_at DESC);
```

---

### 2.8 ai_feedback

Stores user feedback on specific AI chatbot responses.

```sql
CREATE TABLE ai_feedback (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    rating      INTEGER NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ai_feedback_rating_check CHECK (rating IN (1, 2))
);
```

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `message_id` | UUID | No | — | FK to `messages.id` (the assistant response being rated) |
| `rating` | INTEGER | No | — | `1` = thumbs down, `2` = thumbs up |
| `comment` | TEXT | Yes | — | Optional text feedback |
| `created_at` | TIMESTAMPTZ | No | `now()` | Feedback timestamp |

**Constraints:**
- `ai_feedback_rating_check` — `rating` must be 1 or 2
- `ai_feedback_message_id_fkey` — `message_id` references `messages(id)` with `ON DELETE CASCADE`

**Indexes:**
```sql
CREATE INDEX idx_ai_feedback_message_id ON ai_feedback (message_id);
CREATE INDEX idx_ai_feedback_rating ON ai_feedback (rating);
CREATE INDEX idx_ai_feedback_created_at ON ai_feedback (created_at DESC);
```

---

## 3. Entity Relationship Diagram

```
users
  (standalone — admin/staff accounts)

leads
  ↑
  │ lead_id (nullable FK)
  │
conversations
  │                   ↑
  │ conversation_id   │ conversation_id (nullable FK)
  │ (FK, CASCADE)     │
  ↓                   │
messages           analytics_events
  ↑
  │ message_id (FK, CASCADE)
  │
ai_feedback

knowledge_documents
  ↑
  │ document_id (FK, CASCADE)
  │
knowledge_chunks
  (embedding: VECTOR(1536), HNSW index)
```

**Key relationships:**

| From | To | Relationship | FK Column | On Delete |
|------|----|-------------|-----------|-----------|
| conversations | leads | Many-to-one (optional) | `lead_id` | SET NULL |
| messages | conversations | Many-to-one (required) | `conversation_id` | CASCADE |
| analytics_events | conversations | Many-to-one (optional) | `conversation_id` | SET NULL |
| ai_feedback | messages | Many-to-one (required) | `message_id` | CASCADE |
| knowledge_chunks | knowledge_documents | Many-to-one (required) | `document_id` | CASCADE |

---

## 4. Migration Order

Apply migrations in this order:

1. `CREATE EXTENSION IF NOT EXISTS vector;`
2. `users` — no dependencies
3. `leads` — no dependencies
4. `conversations` — depends on `leads`
5. `messages` — depends on `conversations`
6. `knowledge_documents` — no dependencies
7. `knowledge_chunks` — depends on `knowledge_documents`
8. `analytics_events` — depends on `conversations`
9. `ai_feedback` — depends on `messages`

---

## 5. Seed Data

After applying migrations, seed the initial admin user:

```sql
INSERT INTO users (email, password_hash, role)
VALUES (
    'admin@krystalstudio.com',
    '$2b$12$...hashed_password...',
    'owner'
);
```

The password hash is generated using bcrypt with 12 rounds.

---

## 6. Configuration

### 6.1 PostgreSQL Version

- PostgreSQL 16 or higher
- `pgvector` extension (version 0.7+)

### 6.2 Docker Setup (Local Development)

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: krystal_studio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### 6.3 Connection String Format

```
postgresql://<user>:<password>@<host>:<port>/<database>
```

For local development:
```
postgresql://postgres:postgres@localhost:5432/krystal_studio
```

---

## 7. Vector Search Configuration

### 7.1 Embedding Model

- **Model:** OpenAI `text-embedding-3-large`
- **Dimensions:** 1536 (using `dimensions` parameter for cost/performance balance)
- **Distance metric:** Cosine similarity

### 7.2 Chunking Defaults

| Parameter | Value |
|-----------|-------|
| Chunk size | 500–900 tokens (~2,000–3,500 characters) |
| Overlap | 80–150 tokens |
| Top-K retrieval | 4–6 chunks |
| Similarity threshold | 0.7 (configurable via admin settings) |

### 7.3 Retrieval Query

```sql
SELECT
    kc.id,
    kc.chunk_text,
    kc.document_id,
    kc.service_type,
    kc.language,
    kd.title AS document_title,
    1 - (kc.embedding <=> $1::vector) AS similarity
FROM knowledge_chunks kc
JOIN knowledge_documents kd ON kd.id = kc.document_id
WHERE kd.status = 'active'
  AND (kc.language = $2 OR kc.language = 'en')
  AND ($3::text IS NULL OR kc.service_type = $3)
ORDER BY kc.embedding <=> $1::vector
LIMIT $4;
```

The query:
1. Joins chunks with their parent documents
2. Filters to active documents only
3. Prefers the user's selected language, falls back to English
4. Optionally filters by service type
5. Returns the top-K most similar chunks by cosine distance
