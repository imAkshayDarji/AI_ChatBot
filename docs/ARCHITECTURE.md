# Architecture Document — KrystalStudio AI Chatbot Platform

> This document is the architectural source of truth. All implementation must conform to the structures, flows, and boundaries described here.

---

## 1. High-Level System Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                        Customer Browser                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Krystal Tattoo Studio Website                               │ │
│  │  ┌──────────────┐  ┌──────────────────────────────────────┐ │ │
│  │  │  Studio Info  │  │  Embedded Chat Widget                │ │ │
│  │  │  (Static)     │  │  (React + TypeScript)                │ │ │
│  │  └──────────────┘  └──────────────┬───────────────────────┘ │ │
│  └───────────────────────────────────┼─────────────────────────┘ │
└──────────────────────────────────────┼───────────────────────────┘
                                       │ HTTPS / WebSocket
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Vercel (Edge Network)                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Next.js Frontend (SSR/SSG + Client Components)             │ │
│  │  - Public pages                                              │ │
│  │  - Chat widget UI                                            │ │
│  │  - Admin dashboard (protected)                               │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTPS API calls
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Railway (Cloud Runtime)                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  FastAPI Backend                                             │ │
│  │  - Public chat endpoints                                     │ │
│  │  - Admin endpoints (JWT-protected)                           │ │
│  │  - RAG pipeline                                              │ │
│  │  - Lead capture                                              │ │
│  │  - Analytics tracking                                        │ │
│  └──────────┬───────────────────────────┬──────────────────────┘ │
│             │                           │                         │
│             ▼                           ▼                         │
│  ┌──────────────────────┐  ┌────────────────────────────────┐   │
│  │  Railway PostgreSQL   │  │  AI Provider (OpenAI)           │   │
│  │  + pgvector           │  │  - GPT-4o-mini (chat)          │   │
│  │  - Relational data    │  │  - text-embedding-3-large      │   │
│  │  - Vector embeddings  │  │                                  │   │
│  │  - HNSW indexes       │  │                                  │   │
│  └──────────────────────┘  └────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Role | Hosting |
|-----------|------|---------|
| Next.js Frontend | Serves website, chat widget, admin dashboard | Vercel |
| FastAPI Backend | Handles all API logic, AI orchestration, business rules | Railway |
| PostgreSQL + pgvector | Stores relational data and vector embeddings | Railway |
| AI Provider | Generates chat completions and embeddings | OpenAI |

---

## 2. Backend Runtime Flow

Every chat message follows this pipeline:

```text
User sends message
       │
       ▼
┌─────────────────┐
│  FastAPI Route   │  POST /api/v1/chat/message
│  (chat.py)       │  Validates request with Pydantic schema
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator    │  services/chat/orchestrator.py
│                  │  Coordinates the full message pipeline
└────────┬────────┘
         │
         ├──── 1. Load or create conversation
         │         services/chat/memory.py
         │
         ├──── 2. Store user message
         │         db/models/message.py
         │
         ├──── 3. Detect language
         │         services/ai/language.py
         │
         ├──── 4. Classify intent
         │         services/chat/intent.py
         │
         ├──── 5. Run safety checks
         │         services/ai/safety.py
         │         (prompt injection, medical, age)
         │
         ├──── 6. Retrieve relevant knowledge (RAG)
         │         services/rag/retriever.py
         │         → Query embedding → pgvector search → top-K chunks
         │
         ├──── 7. Build prompt
         │         services/ai/prompt_builder.py
         │         (system prompt + knowledge + history + user message)
         │
         ├──── 8. Call AI provider
         │         services/ai/provider.py
         │         (model routing: cheap vs strong)
         │
         ├──── 9. Apply handoff/lead logic
         │         services/leads/extractor.py
         │         (confidence check, lead capture suggestion)
         │
         ├──── 10. Store assistant response
         │          db/models/message.py
         │
         ├──── 11. Track analytics event
         │          services/analytics/tracker.py
         │
         └──── 12. Return response to frontend
                    Pydantic ChatMessageResponse schema
```

---

## 3. RAG Flow

### 3.1 Ingestion Pipeline

```text
Knowledge Sources                    Admin Input
┌──────────────┐                    ┌──────────────┐
│ Website pages │                    │ Manual entry  │
│ FAQs          │                    │ via admin UI  │
│ PDFs          │                    └──────┬───────┘
│ Policies      │                           │
│ Service docs  │                           │
│ Pricing       │                           │
│ Aftercare     │                           │
│ Artist info   │                           │
└──────┬───────┘                           │
       │                                   │
       └───────────┬───────────────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  Ingestion       │  services/rag/ingestion.py
          │  - Clean text    │  - Strip HTML/whitespace
          │  - Normalize     │  - Remove duplicates
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  Chunker         │  services/rag/chunker.py
          │  - 500-900 tokens│  - Overlap: 80-150 tokens
          │  - Service-aware │  - Keep FAQ Q+A together
          │  - Language-aware│  - Keep aftercare steps together
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  Embeddings      │  services/rag/embeddings.py
          │  - OpenAI API    │  - text-embedding-3-large
          │  - Batch support │  - 1536 dimensions
          │  - Store hash    │  - Skip unchanged docs
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────────────┐
          │  PostgreSQL + pgvector   │
          │  knowledge_chunks table  │
          │  - chunk_text            │
          │  - embedding VECTOR(1536)│
          │  - HNSW index            │
          │  - metadata (lang, type) │
          └─────────────────────────┘
```

### 3.2 Retrieval Pipeline

```text
User query: "How much does a small tattoo cost?"
       │
       ▼
┌─────────────────┐
│  Query Embedding  │  Embed user query using same model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  pgvector Search │  SELECT ... ORDER BY embedding <=> query_embedding
│  - Prefer lang   │  WHERE language = user_lang OR language = 'en'
│  - Top-K: 4-6    │  LIMIT 6
│  - Threshold     │  WHERE similarity > threshold
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Evaluate        │  services/rag/evaluator.py
│  - Enough context?│  - Check similarity scores
│  - Relevant?     │  - Check service_type match
└────────┬────────┘
         │
         ├──── Good results → Build prompt with context
         │
         └──── No good results → Trigger handoff or safe fallback
```

---

## 4. Monorepo Structure

```text
KrystalStudio/
│
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py               # Application entry point
│   │   │   ├── core/                 # Config, security, logging, errors
│   │   │   ├── db/                   # Database session, models, base
│   │   │   ├── api/                  # Route handlers
│   │   │   │   ├── deps.py           # Dependency injection
│   │   │   │   └── v1/               # API version 1 routes
│   │   │   ├── schemas/              # Pydantic request/response schemas
│   │   │   ├── services/             # Business logic layer
│   │   │   │   ├── ai/               # AI provider, prompts, safety
│   │   │   │   ├── rag/              # Ingestion, chunking, embeddings, retrieval
│   │   │   │   ├── chat/             # Orchestrator, memory, intent
│   │   │   │   ├── leads/            # Extractor, service, notifier
│   │   │   │   ├── analytics/        # Tracker, queries
│   │   │   │   └── admin/            # Audit
│   │   │   ├── workers/              # Background tasks
│   │   │   └── tests/                # Unit, integration, AI eval tests
│   │   ├── alembic/                  # Database migrations
│   │   ├── requirements.txt          # Python dependencies
│   │   └── Dockerfile
│   │
│   └── web/                          # Next.js frontend
│       ├── app/
│       │   ├── page.tsx              # Public homepage
│       │   ├── layout.tsx            # Root layout
│       │   └── admin/                # Admin dashboard pages
│       ├── components/
│       │   ├── chat/                 # Chat widget components
│       │   ├── admin/                # Admin dashboard components
│       │   └── ui/                   # Shared UI components (shadcn)
│       ├── lib/                      # API client, auth, validators
│       ├── types/                    # TypeScript type definitions
│       └── public/                   # Static assets (logo, icons)
│
├── packages/
│   └── shared/                       # Shared types/constants (future)
│
├── docs/                             # All project documentation
│   ├── ARCHITECTURE.md
│   ├── PRODUCT_SPEC.md
│   ├── API_CONTRACT.md
│   ├── DATABASE_SCHEMA.md
│   ├── AI_SYSTEM.md
│   ├── SECURITY.md
│   ├── DEPLOYMENT.md
│   ├── TESTING.md
│   └── plans/                        # Weekly implementation plans
│
├── infra/                            # Infrastructure configs
│   ├── railway/
│   ├── vercel/
│   └── docker/
│
├── scripts/                          # Utility scripts
│   ├── seed_admin.py
│   ├── seed_knowledge.py
│   └── backup_db.sh
│
├── .cursor/                          # Cursor IDE rules
│   └── rules/
│
├── .github/                          # GitHub Actions workflows
│   └── workflows/
│
├── PLAN.md                           # Master implementation plan
└── README.md                         # Project overview
```

---

## 5. Backend Structure

```text
apps/api/app/
│
├── main.py                           # FastAPI app creation, CORS, lifespan
│
├── core/
│   ├── config.py                     # Settings from env vars (Pydantic BaseSettings)
│   ├── security.py                   # JWT creation/verification, password hashing
│   ├── logging.py                    # Structured logging setup
│   ├── errors.py                     # Global exception handlers
│   └── rate_limit.py                 # Rate limiting middleware
│
├── db/
│   ├── session.py                    # Async SQLAlchemy session factory
│   ├── base.py                       # Declarative base for models
│   └── models/
│       ├── user.py                   # Admin/staff user model
│       ├── lead.py                   # Customer lead model
│       ├── conversation.py           # Chat session model
│       ├── message.py                # Chat message model
│       ├── knowledge.py              # Knowledge document + chunk models
│       ├── analytics.py              # Analytics event model
│       └── feedback.py               # AI feedback model
│
├── api/
│   ├── deps.py                       # Shared dependencies (get_db, get_current_user)
│   └── v1/
│       ├── router.py                 # v1 router aggregating all sub-routers
│       ├── health.py                 # GET /health
│       ├── chat.py                   # POST /chat/start, /chat/message, /chat/feedback
│       ├── leads.py                  # POST /leads (public)
│       ├── admin_auth.py             # POST /admin/auth/login, GET /admin/me
│       ├── admin_leads.py            # Admin lead CRUD
│       ├── admin_chats.py            # Admin chat history
│       ├── admin_knowledge.py        # Admin knowledge CRUD + reindex
│       ├── admin_analytics.py        # Admin analytics endpoints
│       └── admin_settings.py         # Admin settings CRUD
│
├── schemas/
│   ├── auth.py                       # LoginRequest, TokenResponse, UserResponse
│   ├── chat.py                       # ChatStart, ChatMessage, ChatMessageResponse
│   ├── lead.py                       # LeadCreate, LeadUpdate, LeadResponse
│   ├── knowledge.py                  # KnowledgeDocumentCreate/Update/Response
│   ├── analytics.py                  # AnalyticsOverview, PopularIntent, FailedQuery
│   └── common.py                     # PaginatedResponse, ErrorResponse, HealthResponse
│
├── services/
│   ├── ai/
│   │   ├── provider.py               # AI provider abstraction (chat + embeddings)
│   │   ├── model_router.py           # Model selection logic (cheap vs strong)
│   │   ├── prompt_builder.py         # System prompt construction
│   │   ├── safety.py                 # Prompt injection detection, content safety
│   │   ├── language.py               # Language detection
│   │   └── prompts/
│   │       ├── system_prompts.py      # Brand tone, studio info, rules
│   │       ├── safety_prompts.py      # Medical, age, injection refusal
│   │       └── recommendation_prompts.py  # Service recommendation logic
│   │
│   ├── rag/
│   │   ├── ingestion.py              # Document ingestion pipeline
│   │   ├── chunker.py                # Text chunking with metadata
│   │   ├── embeddings.py             # Embedding generation service
│   │   ├── retriever.py              # pgvector similarity search
│   │   └── evaluator.py              # Retrieval quality evaluation
│   │
│   ├── chat/
│   │   ├── orchestrator.py           # Main chat message pipeline
│   │   ├── memory.py                 # Conversation history management
│   │   └── intent.py                 # Intent classification
│   │
│   ├── leads/
│   │   ├── extractor.py              # Lead data extraction from conversation
│   │   ├── service.py                # Lead CRUD operations
│   │   └── notifier.py               # Lead notification (future: email/WhatsApp)
│   │
│   ├── analytics/
│   │   ├── tracker.py                # Event tracking service
│   │   └── queries.py                # Analytics aggregation queries
│   │
│   └── admin/
│       └── audit.py                  # Admin action logging
│
├── workers/
│   ├── reindex_knowledge.py          # Background reindex task
│   └── summarize_conversations.py    # Conversation summarization task
│
└── tests/
    ├── unit/                         # Service unit tests
    ├── integration/                  # API integration tests
    └── ai_eval/                      # AI quality evaluation tests
```

### Data Flow Through Backend Layers

```text
Request (HTTP)
     │
     ▼
Route Handler (api/v1/*.py)
  - Validate request body with Pydantic schema
  - Call service layer
  - Return Pydantic response schema
     │
     ▼
Service Layer (services/**/*.py)
  - Business logic
  - Orchestration
  - AI calls via provider
  - RAG retrieval via retriever
     │
     ▼
Database Layer (db/models/*.py)
  - SQLAlchemy async models
  - Relationships
  - Vector columns
     │
     ▼
PostgreSQL + pgvector
```

---

## 6. Frontend Structure

```text
apps/web/
│
├── app/
│   ├── page.tsx                      # Public homepage with embedded chat
│   ├── layout.tsx                    # Root layout (fonts, metadata, providers)
│   │
│   └── admin/
│       ├── login/page.tsx            # Admin login form
│       ├── dashboard/page.tsx        # Overview: stats, recent leads, charts
│       ├── leads/page.tsx            # Lead table with filters, status updates
│       ├── chats/page.tsx            # Conversation list + transcript viewer
│       ├── knowledge/page.tsx        # Knowledge document editor
│       ├── analytics/page.tsx        # Analytics charts and tables
│       └── settings/page.tsx         # Studio settings configuration
│
├── components/
│   ├── chat/
│   │   ├── ChatWidget.tsx            # Main chat container (floating button + panel)
│   │   ├── LanguageSelector.tsx      # EN/HI/GU language toggle
│   │   ├── MessageBubble.tsx         # Individual message display
│   │   ├── QuickReplies.tsx          # Suggested reply buttons
│   │   ├── LeadCaptureForm.tsx       # Name/email/phone/service form
│   │   └── HandoffCard.tsx           # "Contact studio directly" CTA
│   │
│   ├── admin/
│   │   ├── AdminLayout.tsx           # Sidebar + header wrapper
│   │   ├── Sidebar.tsx               # Admin navigation sidebar
│   │   ├── LeadTable.tsx             # Lead data table with actions
│   │   ├── ChatTranscript.tsx        # Full conversation viewer
│   │   ├── KnowledgeEditor.tsx       # Rich text editor for knowledge docs
│   │   └── AnalyticsCards.tsx        # Metric cards for dashboard
│   │
│   └── ui/                           # shadcn/ui components
│       ├── button.tsx
│       ├── input.tsx
│       ├── card.tsx
│       ├── dialog.tsx
│       ├── table.tsx
│       └── ...
│
├── lib/
│   ├── api.ts                        # Centralized API client (fetch wrapper)
│   ├── auth.ts                       # JWT token management
│   ├── validators.ts                 # Client-side validation helpers
│   └── constants.ts                  # App-wide constants
│
├── types/
│   └── api.ts                        # TypeScript types matching backend schemas
│
└── public/
    ├── logo.jpg                      # Krystal Tattoo Studio logo
    └── favicon.ico
```

---

## 7. Deployment Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                      Production                           │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Vercel                                             │  │
│  │  - Next.js frontend                                │  │
│  │  - Auto-deploy from main branch                    │  │
│  │  - Preview deployments for PRs                     │  │
│  │  - Edge CDN for static assets                      │  │
│  │  - Env: NEXT_PUBLIC_API_URL                        │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │                               │
│                           │ HTTPS                         │
│                           ▼                               │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Railway                                            │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  FastAPI Backend                              │  │  │
│  │  │  - Dockerfile deployment                      │  │  │
│  │  │  - Health check: GET /api/v1/health           │  │  │
│  │  │  - Auto-deploy from main branch               │  │  │
│  │  │  - Env: DATABASE_URL, JWT_SECRET, etc.        │  │  │
│  │  └──────────────────────┬───────────────────────┘  │  │
│  │                         │                           │  │
│  │                         ▼                           │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  Railway PostgreSQL + pgvector                │  │  │
│  │  │  - 8 core tables                              │  │  │
│  │  │  - HNSW vector index                          │  │  │
│  │  │  - Automated backups                          │  │  │
│  │  │  - Connection pooling                         │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  External: OpenAI API                               │  │
│  │  - GPT-4o-mini for chat                            │  │
│  │  - text-embedding-3-large for embeddings           │  │
│  │  - Env: OPENAI_API_KEY (backend only)              │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Environment Variables

**Backend (Railway):**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Token signing key |
| `JWT_ALGORITHM` | Token algorithm (HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `AI_PROVIDER` | AI provider identifier (openai) |
| `OPENAI_API_KEY` | OpenAI API key |
| `CHAT_MODEL` | Chat model name (gpt-4o-mini) |
| `EMBEDDING_MODEL` | Embedding model name |
| `CORS_ORIGINS` | Allowed frontend origins |
| `STUDIO_PHONE` | Studio phone for handoff |
| `STUDIO_INSTAGRAM_URL` | Instagram URL for handoff |
| `ENVIRONMENT` | production / development |

**Frontend (Vercel):**

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |
| `NEXT_PUBLIC_STUDIO_NAME` | Studio display name |

---

## 8. Data Flow Diagrams

### 8.1 Chat Conversation Flow

```text
Browser                    Vercel/Next.js              Railway/FastAPI           PostgreSQL          OpenAI
  │                             │                           │                       │                 │
  │  User types message         │                           │                       │                 │
  │─────────────────────────────>│                           │                       │                 │
  │                             │  POST /api/v1/chat/message│                       │                 │
  │                             │──────────────────────────>│                       │                 │
  │                             │                           │  Load conversation     │                 │
  │                             │                           │──────────────────────>│                 │
  │                             │                           │<──────────────────────│                 │
  │                             │                           │                       │                 │
  │                             │                           │  Store user message    │                 │
  │                             │                           │──────────────────────>│                 │
  │                             │                           │                       │                 │
  │                             │                           │  Detect language       │                 │
  │                             │                           │  Classify intent       │                 │
  │                             │                           │  Run safety checks     │                 │
  │                             │                           │                       │                 │
  │                             │                           │  Embed query + Search  │                 │
  │                             │                           │──────────────────────>│                 │
  │                             │                           │  Top-K chunks          │                 │
  │                             │                           │<──────────────────────│                 │
  │                             │                           │                       │                 │
  │                             │                           │  Chat completion       │                 │
  │                             │                           │──────────────────────────────────────────>│
  │                             │                           │<──────────────────────────────────────────│
  │                             │                           │                       │                 │
  │                             │                           │  Store response        │                 │
  │                             │                           │  Track analytics       │                 │
  │                             │                           │──────────────────────>│                 │
  │                             │                           │                       │                 │
  │                             │  ChatMessageResponse      │                       │                 │
  │                             │<──────────────────────────│                       │                 │
  │  Display response           │                           │                       │                 │
  │<─────────────────────────────│                           │                       │                 │
```

### 8.2 Knowledge Ingestion Flow

```text
Admin Browser         Vercel/Next.js           Railway/FastAPI          PostgreSQL       OpenAI
  │                        │                          │                      │                │
  │  Create knowledge doc  │                          │                      │                │
  │───────────────────────>│                          │                      │                │
  │                        │  POST /admin/knowledge   │                      │                │
  │                        │─────────────────────────>│                      │                │
  │                        │                          │  Save document       │                │
  │                        │                          │─────────────────────>│                │
  │                        │                          │                      │                │
  │                        │                          │  Clean + chunk text  │                │
  │                        │                          │                      │                │
  │                        │                          │  Generate embeddings                    │
  │                        │                          │──────────────────────────────────────>│
  │                        │                          │<──────────────────────────────────────│
  │                        │                          │                      │                │
  │                        │                          │  Store chunks + vectors                │
  │                        │                          │─────────────────────>│                │
  │                        │                          │                      │                │
  │                        │  Document response       │                      │                │
  │                        │<─────────────────────────│                      │                │
  │  Show success          │                          │                      │                │
  │<───────────────────────│                          │                      │                │
```

### 8.3 Lead Capture Flow

```text
Browser                 Vercel/Next.js            Railway/FastAPI          PostgreSQL
  │                          │                          │                      │
  │  Chat suggests lead form │                          │                      │
  │<─────────────────────────│                          │                      │
  │                          │                          │                      │
  │  User fills name/email   │                          │                      │
  │─────────────────────────>│                          │                      │
  │                          │  POST /api/v1/leads      │                      │
  │                          │─────────────────────────>│                      │
  │                          │                          │  Create lead         │
  │                          │                          │─────────────────────>│
  │                          │                          │                      │
  │                          │                          │  Link to conversation│
  │                          │                          │─────────────────────>│
  │                          │                          │                      │
  │                          │  Lead response           │                      │
  │                          │<─────────────────────────│                      │
  │  Show confirmation       │                          │                      │
  │<─────────────────────────│                          │                      │
```

---

## 9. Security Boundaries

### 9.1 Public vs Admin Boundary

```text
┌─────────────────────────────────────────────────────────────┐
│                      Public Zone                              │
│                                                               │
│  Routes:                                                      │
│    GET  /api/v1/health                                        │
│    POST /api/v1/chat/start                                    │
│    POST /api/v1/chat/message                                  │
│    POST /api/v1/chat/feedback                                 │
│    POST /api/v1/leads                                         │
│                                                               │
│  Rules:                                                       │
│    - No authentication required                               │
│    - Rate limited (per IP/session)                            │
│    - Input validated with Pydantic                            │
│    - Max message length enforced                              │
│    - No access to admin data                                  │
│    - No access to other users' conversations                  │
│    - Prompt injection guardrails active                       │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Admin Zone                               │
│                                                               │
│  Routes:                                                      │
│    POST /api/v1/admin/auth/login                              │
│    GET  /api/v1/admin/me                                      │
│    GET  /api/v1/admin/leads                                   │
│    GET  /api/v1/admin/leads/{id}                              │
│    PATCH /api/v1/admin/leads/{id}                             │
│    GET  /api/v1/admin/chats                                   │
│    GET  /api/v1/admin/chats/{id}                              │
│    GET  /api/v1/admin/knowledge                               │
│    POST /api/v1/admin/knowledge                               │
│    GET  /api/v1/admin/knowledge/{id}                          │
│    PATCH /api/v1/admin/knowledge/{id}                         │
│    DELETE /api/v1/admin/knowledge/{id}                        │
│    POST /api/v1/admin/knowledge/{id}/reindex                  │
│    GET  /api/v1/admin/analytics/overview                      │
│    GET  /api/v1/admin/analytics/popular-intents               │
│    GET  /api/v1/admin/analytics/failed-queries                │
│    GET  /api/v1/admin/settings                                │
│    PATCH /api/v1/admin/settings                               │
│                                                               │
│  Rules:                                                       │
│    - JWT authentication required                              │
│    - Role-based access (owner > admin > staff)                │
│    - Login rate limited                                       │
│    - Password hashed (bcrypt)                                 │
│    - Short-lived access tokens                                │
└───────────────────────────────────────────────────────────────┘
```

### 9.2 Authentication Layer

```text
Login Request
     │
     ▼
POST /api/v1/admin/auth/login
  { email, password }
     │
     ▼
Verify password hash (bcrypt)
     │
     ├── Invalid → 401 Unauthorized
     │
     └── Valid → Generate JWT
              │
              ▼
         Response: { access_token, token_type }
              │
              ▼
         Subsequent requests include:
         Authorization: Bearer <access_token>
              │
              ▼
         get_current_user dependency:
           - Decode JWT
           - Verify signature
           - Check expiry
           - Load user from DB
           - Attach to request state
```

### 9.3 CORS Configuration

```text
Allowed Origins:
  - https://krystaltattoostudio.com (production)
  - https://*.vercel.app (preview deployments)
  - http://localhost:3000 (local development)

Allowed Methods:
  - GET, POST, PATCH, DELETE, OPTIONS

Allowed Headers:
  - Authorization, Content-Type

Credentials:
  - Allowed (for admin JWT)
```

### 9.4 Trust Boundaries

| Boundary | Trust Level | Validation |
|----------|-------------|------------|
| Browser → Frontend | Untrusted | Client validation only |
| Frontend → Backend API | Untrusted | Pydantic schema validation |
| Backend → Database | Trusted (internal) | Parameterized queries |
| Backend → AI Provider | Trusted (internal) | API key auth |
| User message → AI prompt | Untrusted | Safety checks, injection detection |
| RAG retrieved text → AI prompt | Semi-trusted | Evaluated by similarity threshold |
| Admin user → Admin API | Authenticated | JWT + role check |

---

## 10. Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | Next.js | Latest |
| Frontend Language | TypeScript | 5.x |
| CSS Framework | Tailwind CSS | v4 |
| UI Components | shadcn/ui | Latest |
| Backend Framework | FastAPI | Latest |
| Backend Language | Python | 3.12 |
| ORM | SQLAlchemy (async) | 2.x |
| Migrations | Alembic | Latest |
| Validation | Pydantic | v2 |
| Database | PostgreSQL | 16 |
| Vector Extension | pgvector | Latest |
| AI Provider | OpenAI | GPT-4o-mini |
| Embeddings | OpenAI | text-embedding-3-large |
| Authentication | JWT | python-jose |
| Password Hashing | bcrypt | passlib |
| Frontend Hosting | Vercel | — |
| Backend Hosting | Railway | — |
| Package Manager | pnpm | Latest |
| Node.js | 20 LTS | — |
| Development IDE | Cursor | — |
| AI Coding Assistant | GLM-5.1 | — |

---

## 11. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monorepo vs multi-repo | Monorepo | Easier context, local dev, deployment coordination for solo/small team |
| Modular monolith vs microservices | Modular monolith | Faster MVP, lower cost, simpler debugging, clean extraction path |
| pgvector vs external vector DB | pgvector | Lower cost, simpler deployment, one database, good for small knowledge bases |
| FastAPI vs Django | FastAPI | Async-first, lightweight, better for API-only backend |
| Next.js vs plain React | Next.js | SSR/SSG, API routes, Vercel integration, file-based routing |
| JWT vs session auth | JWT | Stateless, works across domains, standard for SPAs |
| HNSW vs IVFFlat index | HNSW | Better recall for small/medium datasets, faster queries |
