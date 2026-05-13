# TODOS

## [P2] Add IVFFlat (or compatible) pgvector index for 3072-d embeddings
- **What:** After chunk backfill, create an approximate index (e.g. IVFFlat with cosine ops) suitable for `vector(3072)`, or upgrade pgvector/build flags that raise the HNSW dimension cap.
- **Why:** HNSW in current pgvector rejects dimensions > 2000. Week 3 migration drops the old HNSW index; queries use sequential scan until a supported index exists.
- **Context:** Week 3 Task 3.0; `002_embedding_3072.py` documents the limitation.
- **Effort:** M
- **Priority:** P2
- **Added:** 2026-05-13

## [P2] Add GitHub Actions CI workflow
- **What:** Create `.github/workflows/ci.yml` that runs pytest on push to main and PRs.
- **Why:** Catches broken tests before they land. Standard practice for any repo with tests.
- **Pros:** Automated safety net, enforces test discipline.
- **Cons:** ~30 lines YAML, minor maintenance.
- **Context:** Week 1 creates the workflows directory but leaves it empty. Add in Week 2 when real tests exist.
- **Effort:** S (CC: ~3 min)
- **Depends on:** Week 2 tests
- **Added:** 2026-05-13 (CEO review of Week 1)
- **Status:** PROMOTED to Week 2 scope (accepted via CEO review cherry-pick)

## [P2] Add Redis-backed distributed rate limiting
- **What:** Replace in-memory rate limiting with Redis-backed rate limiting via slowapi + Redis backend.
- **Why:** In-memory rate limiting doesn't work across multiple Railway instances. If the backend scales to 2+ containers, rate limits are per-container, not global.
- **Pros:** Production-grade rate limiting. Works across multiple instances.
- **Cons:** Adds Redis as a dependency. Slightly more complex configuration.
- **Context:** Week 2 adds simple in-memory rate limiting on login. This upgrades it to distributed.
- **Effort:** S (CC: ~5 min)
- **Priority:** P2
- **Depends on:** Redis instance on Railway (Week 6)
- **Added:** 2026-05-13 (CEO review of Week 2)

## [P3] Add password reset flow
- **What:** Password reset endpoint that generates a time-limited reset token, sends it via email, and allows setting a new password.
- **Why:** Admin lockout is a real operational risk. If the seed-generated password is lost, the only recovery is re-running the seed script or direct DB manipulation.
- **Pros:** Self-service password recovery. Standard for any admin panel.
- **Cons:** Requires an email service (SendGrid, Mailgun, or SMTP). Adds a `password_reset_tokens` table.
- **Context:** Week 2 builds auth but no reset mechanism. The seed script auto-generates passwords.
- **Effort:** M (CC: ~30 min)
- **Priority:** P3
- **Depends on:** Email service integration (post-MVP)
- **Added:** 2026-05-13 (CEO review of Week 2)

## [P2] Add hybrid search (vector + keyword BM25) to retrieval
- **What:** Combine pgvector cosine similarity with PostgreSQL full-text search (tsvector/tsquery) for better retrieval on exact keyword matches like pricing amounts and phone numbers.
- **Why:** Pure vector search is bad at exact matches. A user asking for the studio phone number won't get the right chunk if the embedding similarity is low on the number string.
- **Pros:** Better recall on factual queries. Industry standard for production RAG.
- **Cons:** Adds tsvector column to knowledge_chunks. More complex retrieval query.
- **Context:** Week 3 builds pure vector retrieval. Hybrid search significantly improves accuracy for factual/exact-match queries without adding external dependencies.
- **Effort:** M (human ~1 day / CC ~30 min)
- **Priority:** P2
- **Depends on:** Week 3 completion
- **Added:** 2026-05-13 (CEO review of Week 3)

## [P2] Add content-hash based ingestion idempotency
- **What:** Store a content hash on knowledge_documents. On reindex, skip documents whose content hasn't changed. Prevents wasting OpenAI tokens on unchanged documents.
- **Why:** Admin clicks "reindex all" on 50 documents. 45 haven't changed. That's 45 unnecessary embedding API calls costing real money.
- **Pros:** Saves OpenAI costs. Faster bulk reindex.
- **Cons:** Needs a `content_hash` column and migration.
- **Context:** Week 3 ingestion pipeline has no intelligence around unchanged content. Every reindex is a full re-embed.
- **Effort:** S (CC ~15 min)
- **Priority:** P2
- **Depends on:** Week 3 completion
- **Added:** 2026-05-13 (CEO review of Week 3)

## [P2] Add admin endpoint to inspect chunks for a document
- **What:** `GET /admin/knowledge/{id}/chunks` returns the list of chunks with their text, chunk_index, service_type, and language. No embeddings returned.
- **Why:** After reindexing, admins have no way to verify the chunks look correct. They can't tell if the chunker split in the wrong place or if metadata is wrong.
- **Pros:** Debuggability. Admin confidence in indexed data.
- **Cons:** Small API surface addition.
- **Context:** Week 3 creates chunks but provides no way to inspect them. Admins are flying blind on chunk quality.
- **Effort:** S (CC ~10 min)
- **Priority:** P2
- **Depends on:** Week 3 completion
- **Added:** 2026-05-13 (CEO review of Week 3)
