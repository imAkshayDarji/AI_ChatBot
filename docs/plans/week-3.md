# Week 3 — RAG Pipeline and AI Core

> **Status:** NOT STARTED
> **Depends on:** Week 2 completed
> **Blocks:** Week 4

---

## Goal

System can ingest knowledge documents (clean, chunk, embed), store vectors in pgvector, retrieve relevant chunks for queries, and generate AI responses through an abstracted provider.

---

## Pre-Implementation Questions (ASK USER BEFORE STARTING)

1. Is your OpenAI API key configured in `.env`? (Required for embeddings and chat)
2. Do you have any existing FAQ or service content to seed the knowledge base? (Text, PDF, or URL)
3. Any specific tattoo styles the studio specializes in? (Used for recommendation prompts)
4. Any piercing types the studio does NOT do? (Used for safety/boundary in responses)

---

## Tasks

### Task 3.1 — Text Cleaning Service

**What:** Create a text cleaning utility for knowledge ingestion.

**Files to create:**

```
apps/api/app/services/rag/cleaner.py
```

**Functions:**

```python
def clean_text(raw: str) -> str:
    """Remove HTML tags, normalize whitespace, fix encoding."""

def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single."""

def remove_html_tags(text: str) -> str:
    """Strip HTML tags from content."""

def detect_language(text: str) -> str:
    """Return 'en', 'hi', or 'gu' based on script detection."""
```

**Constraints:**
- Pure functions, no side effects
- Handle empty strings gracefully
- Do not use heavy NLP libraries for MVP (basic regex is fine)

**Tests:**

```python
# apps/api/app/tests/unit/test_cleaner.py
def test_clean_html():
    assert clean_text("<p>Hello <b>world</b></p>") == "Hello world"

def test_normalize_whitespace():
    assert normalize_whitespace("hello   \n\n  world") == "hello\nworld"

def test_empty_string():
    assert clean_text("") == ""
    assert clean_text("   ") == ""

def test_detect_english():
    assert detect_language("Hello, how much is a tattoo?") == "en"

def test_detect_hindi():
    assert detect_language("टैटू कितने का होता है?") == "hi"

def test_detect_gujarati():
    assert detect_language("ટેટૂ કેટલાનો આવે છે?") == "gu"
```

---

### Task 3.2 — Chunking Service

**What:** Create a document chunker that splits text into searchable segments.

**Files to create:**

```
apps/api/app/services/rag/chunker.py
```

**Configuration (from PLAN.md Section 7.3):**

```python
CHUNK_SIZE = 800  # ~3000 characters target
CHUNK_OVERLAP = 120  # tokens
MIN_CHUNK_SIZE = 100  # don't create tiny chunks
```

**Class:**

```python
class Chunker:
    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP): ...

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into overlapping chunks with metadata."""
        ...

    def chunk_faq(self, questions: list[dict]) -> list[Chunk]:
        """Keep FAQ Q&A pairs together. Each Q&A is one chunk."""
        ...

@dataclass
class Chunk:
    text: str
    index: int
    metadata: dict
```

**Chunking rules from PLAN.md:**
- Keep FAQ question and answer together
- Keep aftercare steps together
- Keep pricing guidance together
- Do not mix tattoo/piercing/dreadlock topics in same chunk if avoidable
- Avoid huge chunks (>1500 chars)
- Avoid tiny chunks without context (<100 chars)

**Tests:**

```python
# apps/api/app/tests/unit/test_chunker.py
def test_chunk_text_basic():
    chunks = Chunker().chunk_text("A " * 2000)
    assert len(chunks) > 1
    assert all(len(c.text) <= 1500 for c in chunks)

def test_chunk_overlap():
    chunks = Chunker(overlap=50).chunk_text("word " * 500)
    # Adjacent chunks should share some text
    ...

def test_chunk_faq_keeps_pairs():
    faqs = [
        {"q": "How much is a small tattoo?", "a": "Starting from ₹2000 depending on..."},
        {"q": "Do you do walk-ins?", "a": "Yes, but appointments preferred..."}
    ]
    chunks = Chunker().chunk_faq(faqs)
    assert len(chunks) == 2
    assert "How much" in chunks[0].text
    assert "₹2000" in chunks[0].text

def test_empty_text_returns_empty():
    assert Chunker().chunk_text("") == []

def test_short_text_returns_single_chunk():
    chunks = Chunker().chunk_text("Short text")
    assert len(chunks) == 1
```

---

### Task 3.3 — Embedding Service

**What:** Create the embedding generation service using OpenAI.

**Files to create:**

```
apps/api/app/services/rag/embeddings.py
```

**Class:**

```python
class EmbeddingService:
    def __init__(self, api_key: str, model: str = "text-embedding-3-large"): ...

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batch)."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a user query."""
        ...
```

**Constraints:**
- All embedding calls MUST go through this service (PLAN.md Rule 1.5)
- Handle API errors with retry (up to 3 attempts)
- Log token usage
- Handle rate limits gracefully
- Batch size limit: 100 texts per call
- Use `text-embedding-3-large` model

**Tests:**

```python
# apps/api/app/tests/unit/test_embeddings.py
async def test_embed_text_returns_vector(mock_openai):
    service = EmbeddingService(api_key="test-key")
    embedding = await service.embed_text("Hello world")
    assert isinstance(embedding, list)
    assert len(embedding) == 3072  # text-embedding-3-large dimension

async def test_embed_texts_batch(mock_openai):
    service = EmbeddingService(api_key="test-key")
    embeddings = await service.embed_texts(["Hello", "World"])
    assert len(embeddings) == 2

async def test_embed_error_handling(mock_openai_error):
    service = EmbeddingService(api_key="test-key")
    with pytest.raises(EmbeddingError):
        await service.embed_text("test")
```

---

### Task 3.4 — Ingestion Pipeline

**What:** Wire up cleaner -> chunker -> embedder -> database storage.

**Files to create:**

```
apps/api/app/services/rag/ingestion.py
```

**Class:**

```python
class IngestionService:
    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService): ...

    async def ingest_document(self, document: KnowledgeDocument) -> list[KnowledgeChunk]:
        """
        Full pipeline:
        1. Clean text
        2. Chunk text
        3. Generate embeddings for all chunks
        4. Delete old chunks for this document
        5. Insert new chunks with embeddings
        6. Mark document status as 'active'
        7. Return created chunks
        """
        ...

    async def delete_document_chunks(self, document_id: UUID) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        ...
```

**Flow:**
```
document.content
    -> clean_text()
    -> chunker.chunk_text()
    -> embedding_service.embed_texts()
    -> delete old chunks
    -> insert new chunks with embeddings
    -> update document.status = "active"
```

**Tests:**

```python
# apps/api/app/tests/unit/test_ingestion.py
async def test_ingest_creates_chunks(db_session, sample_document, mock_embedding):
    service = IngestionService(db_session, mock_embedding)
    chunks = await service.ingest_document(sample_document)
    assert len(chunks) > 0
    assert all(c.embedding is not None for c in chunks)
    assert all(c.document_id == sample_document.id for c in chunks)

async def test_reingest_replaces_chunks(db_session, sample_document, mock_embedding):
    service = IngestionService(db_session, mock_embedding)
    chunks_v1 = await service.ingest_document(sample_document)
    # Modify content and reingest
    sample_document.content = "Updated content " * 500
    chunks_v2 = await service.ingest_document(sample_document)
    # Old chunks should be gone, new ones created
    assert len(chunks_v2) > 0
    # Total chunks in DB should be len(chunks_v2), not len(v1) + len(v2)
```

---

### Task 3.5 — Knowledge Reindex Endpoint (Wire Up)

**What:** Connect the ingestion pipeline to the admin reindex endpoint.

**Files to modify:**

```
apps/api/app/api/v1/admin_knowledge.py  (update reindex endpoint)
```

**Update:**

```python
@router.post("/knowledge/{document_id}/reindex")
async def reindex_document(document_id: UUID, ...):
    document = await knowledge_service.get_document(db, document_id)
    chunks = await ingestion_service.ingest_document(document)
    return {"message": f"Indexed {len(chunks)} chunks", "document_id": str(document_id)}
```

**Also:** Auto-index on document creation if status is "active".

**Tests:**

```python
# apps/api/app/tests/integration/test_knowledge_reindex.py
def test_reindex_document(client, admin_token, sample_document):
    response = client.post(f"/api/v1/admin/knowledge/{sample_document.id}/reindex",
        headers=auth_header(admin_token))
    assert response.status_code == 202
    assert "chunks" in response.json()["message"].lower()
```

---

### Task 3.6 — Retrieval Service

**What:** Create the vector similarity search retriever.

**Files to create:**

```
apps/api/app/services/rag/retriever.py
```

**Class:**

```python
class RetrieverService:
    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService): ...

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        language: str = "en",
        service_type: str | None = None,
        similarity_threshold: float = 0.5,
    ) -> list[RetrievalResult]:
        """
        1. Embed query
        2. Search knowledge_chunks using pgvector cosine similarity
        3. Prefer selected language, fall back to English
        4. Apply similarity threshold
        5. Return top_k results with metadata
        """
        ...

@dataclass
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    chunk_text: str
    score: float
    service_type: str  # always set on row (DB NOT NULL, default general)
    language: str
    source_title: str
```

**SQL query pattern:**

```sql
SELECT kc.*, kd.title as source_title,
       1 - (kc.embedding <=> :query_embedding) as similarity
FROM knowledge_chunks kc
JOIN knowledge_documents kd ON kc.document_id = kd.id
WHERE kd.status = 'active'
  AND (kc.language = :preferred_lang OR kc.language = 'en')
  AND (:service_type IS NULL OR kc.service_type = :service_type)
ORDER BY kc.embedding <=> :query_embedding
LIMIT :top_k
```

**Week 2 alignment:** `knowledge_chunks.service_type` is **NOT NULL** with default **`general`**. Passing `service_type=None` in Python means **omit** the filter (include all chunks). Passing `service_type="tattoo"` restricts to that value; chunks that stayed default `general` still match only when you filter by `general` explicitly.

**Constraints:**
- All retrieval MUST go through this service (PLAN.md Rule 1.5)
- Language fallback: prefer user's language, then English
- Similarity threshold: configurable, default 0.5
- If no results above threshold, return empty list (do NOT invent results)

**Tests:**

```python
# apps/api/app/tests/unit/test_retriever.py
async def test_retrieve_tattoo_query(db_session, tattoo_knowledge):
    results = await retriever.retrieve("How much is a small tattoo?")
    assert len(results) > 0
    assert any("tattoo" in r.chunk_text.lower() for r in results)

async def test_retrieve_piercing_aftercare(db_session, piercing_knowledge):
    results = await retriever.retrieve("How do I clean my new piercing?")
    assert any("piercing" in r.chunk_text.lower() for r in results)
    assert any("aftercare" in r.chunk_text.lower() or "clean" in r.chunk_text.lower() for r in results)

async def test_retrieve_language_fallback(db_session, english_only_knowledge):
    results = await retriever.retrieve("टैटू की कीमत", language="hi")
    # Should fall back to English results
    assert len(results) > 0

async def test_retrieve_no_results(db_session, empty_knowledge):
    results = await retriever.retrieve("quantum physics")
    assert len(results) == 0

async def test_similarity_threshold(db_session, knowledge):
    results = await retriever.retrieve("hello world", similarity_threshold=0.99)
    assert len(results) == 0  # threshold too high
```

---

### Task 3.7 — AI Provider Abstraction

**What:** Create the AI provider interface and OpenAI implementation.

**Files to create:**

```
apps/api/app/services/ai/provider.py
apps/api/app/services/ai/model_router.py
```

**Interface:**

```python
class AIProvider(Protocol):
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AIResponse: ...

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]: ...

@dataclass
class AIResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
```

**OpenAI implementation:**

```python
class OpenAIProvider:
    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"): ...

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=1000) -> AIResponse:
        ...

    async def chat_stream(self, messages, model=None, temperature=0.7) -> AsyncIterator[str]:
        ...  # Placeholder for streaming (Phase 2)
```

**Model router:**

```python
class ModelRouter:
    """
    Routes to appropriate model based on task complexity.
    - Simple FAQ / greetings -> gpt-4o-mini (cheap)
    - Complex recommendations -> gpt-4o (expensive)
    - Static info -> no model (deterministic)
    """
    def select_model(self, intent: str, complexity: str) -> str | None:
        ...
```

**Constraints:**
- All AI calls MUST go through `provider.py` (PLAN.md Rule 1.5)
- Provider selection via `AI_PROVIDER` env var
- Error handling: retry up to 2 times, then raise
- Log token usage per request
- Streaming is placeholder for now (just return full response)

**Tests:**

```python
# apps/api/app/tests/unit/test_ai_provider.py
async def test_openai_chat(mock_openai):
    provider = OpenAIProvider(api_key="test-key")
    response = await provider.chat([{"role": "user", "content": "Hello"}])
    assert response.content
    assert response.model

async def test_model_router_simple():
    router = ModelRouter()
    model = router.select_model(intent="greeting", complexity="simple")
    assert model == "gpt-4o-mini"

async def test_model_router_complex():
    router = ModelRouter()
    model = router.select_model(intent="recommendation", complexity="complex")
    assert model == "gpt-4o"

async def test_provider_error_handling(mock_openai_error):
    provider = OpenAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError):
        await provider.chat([{"role": "user", "content": "Hello"}])
```

---

### Task 3.8 — Seed Knowledge Script

**What:** Create a script to seed sample knowledge for testing.

**Files to create:**

```
scripts/seed_knowledge.py
```

**Sample knowledge documents:**

1. **Tattoo Pricing** — General pricing guidance for small, medium, large tattoos
2. **Tattoo Aftercare** — Step-by-step aftercare instructions
3. **Piercing Services** — Types of piercings offered, general pricing
4. **Piercing Aftercare** — Cleaning and care instructions
5. **Dreadlock Services** — Types of dreadlock services, maintenance info
6. **Studio Policy** — Age requirements, booking policy, cancellation
7. **Opening Hours** — Weekly schedule
8. **FAQ** — Common questions and answers

**Each document includes:**
- English content
- Title and source_type
- service_type metadata (tattoo/piercing/dreadlock/general)

**Requirements:**
- Idempotent
- Auto-indexes (creates chunks and embeddings)
- Uses actual OpenAI API for embeddings

**Verification:**
```bash
python scripts/seed_knowledge.py
# Should create 8 documents with chunks and embeddings
# Verify: SELECT count(*) FROM knowledge_chunks; should return 20+ chunks
```

---

## Testing Checklist (Run After ALL Tasks Complete)

- [ ] Text cleaner handles HTML, whitespace, empty strings
- [ ] Chunker creates proper chunks with overlap
- [ ] Embedding service generates vectors (mock test)
- [ ] Ingestion pipeline: document -> chunks -> embeddings stored in DB
- [ ] Reindex endpoint works via API
- [ ] Retrieval returns relevant chunks for tattoo queries
- [ ] Retrieval returns relevant chunks for piercing queries
- [ ] Retrieval returns relevant chunks for dreadlock queries
- [ ] Language fallback works (Hindi query -> English results)
- [ ] No-result case returns empty list (not error)
- [ ] AI provider chat works (mock test)
- [ ] Model router selects correct model by complexity
- [ ] Seed knowledge script creates documents with embeddings
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Lint passes

---

## Git Commit Strategy

```bash
# After Task 3.1-3.2
git add -A && git commit -m "feat(rag): add text cleaner and document chunker"

# After Task 3.3-3.4
git add -A && git commit -m "feat(rag): add embedding service and ingestion pipeline"

# After Task 3.5-3.6
git add -A && git commit -m "feat(rag): add knowledge reindex and vector retrieval"

# After Task 3.7-3.8
git add -A && git commit -m "feat(ai): add provider abstraction, model router, and seed knowledge"

git push origin main
```

---

## After Week 3 Completion

- [ ] Update PLAN.md checklist — mark Phase 6, 7, 8 items as done
- [ ] Update this file's status to COMPLETED
- [ ] Proceed to `docs/plans/week-4.md`
