# AI System Design

> **Read PLAN.md before making changes to any AI-related code.**
>
> This document is the authoritative reference for the AI subsystem including provider abstraction, prompt construction, RAG pipeline, safety rules, and memory strategy.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [AI Provider Abstraction](#2-ai-provider-abstraction)
3. [Model Routing Strategy](#3-model-routing-strategy)
4. [Prompt Builder](#4-prompt-builder)
5. [Hallucination Prevention](#5-hallucination-prevention)
6. [Medical and Aftercare Rules](#6-medical-and-aftercare-rules)
7. [Age Restriction Rules](#7-age-restriction-rules)
8. [Handoff Triggers and Message Style](#8-handoff-triggers-and-message-style)
9. [RAG Pipeline](#9-rag-pipeline)
10. [Chunking Strategy](#10-chunking-strategy)
11. [Retrieval Strategy](#11-retrieval-strategy)
12. [Memory Strategy](#12-memory-strategy)
13. [Prompt Injection Defense](#13-prompt-injection-defense)
14. [Provider Configuration](#14-provider-configuration)

---

## 1. Architecture Overview

The AI subsystem follows a layered architecture where every AI-related operation passes through well-defined service boundaries:

```text
API Route (apps/api/app/api/v1/chat.py)
     ↓
Chat Orchestrator (apps/api/app/services/chat/orchestrator.py)
     ↓
     ├── Intent Classifier (apps/api/app/services/chat/intent.py)
     ├── Safety Guardrails (apps/api/app/services/ai/safety.py)
     ├── RAG Retriever (apps/api/app/services/rag/retriever.py)
     ├── Prompt Builder (apps/api/app/services/ai/prompt_builder.py)
     ├── AI Provider (apps/api/app/services/ai/provider.py)
     ├── Lead Extractor (apps/api/app/services/leads/extractor.py)
     └── Analytics Tracker (apps/api/app/services/analytics/tracker.py)
```

**Key rules:**

- Route handlers must never call AI providers directly.
- Route handlers must never call embedding services directly.
- All model interactions flow through `provider.py`.
- All embedding interactions flow through `rag/embeddings.py`.
- All retrieval flows through `rag/retriever.py`.
- Business logic lives in service layers, not in routes.

---

## 2. AI Provider Abstraction

**File:** `apps/api/app/services/ai/provider.py`

The provider is the single point of contact between the application and any LLM. It must support:

### 2.1 Chat Generation

- Accept a list of messages (system, user, assistant roles).
- Accept model configuration parameters (temperature, max_tokens, top_p).
- Return the generated message content, finish reason, and token usage.
- Support synchronous generation for simple cases.

### 2.2 Streaming Response

- Accept the same parameters as chat generation.
- Return an async generator yielding response chunks.
- Include a final chunk with token usage statistics.
- Handle early termination gracefully (client disconnect).

### 2.3 Embedding Delegation

- The provider delegates embedding generation to `apps/api/app/services/rag/embeddings.py`.
- The provider does not implement embedding logic itself.
- This separation allows swapping the embedding model independently from the chat model.

### 2.4 Model Selection

- Read model configuration from `apps/api/app/core/config.py`.
- Support configuring different models for different use cases via `model_router.py`.
- Default model: `gpt-4o-mini`.
- Default embedding model: `text-embedding-3-large`.

### 2.5 Error Handling

- Catch and wrap provider-specific exceptions into application-level errors.
- Distinguish between:
  - **Rate limit errors** — return 429 to client, log the event.
  - **Authentication errors** — log alert, return 500 to client (this is a config issue, not a user issue).
  - **Timeout errors** — retry once with backoff, then return a safe fallback response.
  - **Context length exceeded** — truncate context and retry, or hand off.
  - **Content filter triggered** — log the event, return a safe refusal response.
- Never expose raw provider error messages to the end user.

### 2.6 Retry Handling

- Retry transient errors (rate limit, timeout, server error) up to 2 times.
- Use exponential backoff: 1s, 2s between retries.
- Do not retry authentication errors or content filter blocks.
- Log each retry attempt with the reason.

### 2.7 Token Usage Tracking

- After every model call, extract `prompt_tokens`, `completion_tokens`, and `total_tokens`.
- Store token usage in the message `metadata_json` field.
- Emit an analytics event with model name, token counts, and estimated cost.
- Aggregate daily token usage for cost monitoring.

### 2.8 Provider Interface

```python
class AIProvider(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> GenerateResponse: ...

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]: ...


class GenerateResponse:
    content: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
```

---

## 3. Model Routing Strategy

**File:** `apps/api/app/services/ai/model_router.py`

The model router selects the appropriate model and approach based on the classified intent and confidence level.

### 3.1 Routing Ladder

| Intent Category | Confidence | Model | Rationale |
|---|---|---|---|
| Static data (hours, address, contact) | High | No model | Deterministic response from knowledge base |
| Simple FAQ (yes/no, basic info) | High | `gpt-4o-mini` | Fast, cheap, sufficient |
| Pricing guidance | Medium-High | `gpt-4o-mini` | Needs nuance but structured |
| Service recommendations | Medium | `gpt-4o-mini` | Needs context awareness |
| Aftercare guidance | Medium | `gpt-4o-mini` | Sensitive but KB-grounded |
| Complex multi-step queries | Low-Medium | `gpt-4o-mini` with extra context | Needs more reasoning |
| Ambiguous/unclear intent | Low | `gpt-4o-mini` with handoff bias | Err toward safe handoff |

### 3.2 No-Model Responses

For static, deterministic queries, return pre-built responses without calling any LLM:

- Studio opening hours
- Studio address
- Phone number
- Instagram URL
- Basic greeting/welcome message

This reduces cost and latency for the most common queries.

### 3.3 Model Configuration

```python
MODEL_CONFIG = {
    "default": {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1.0,
    },
    "complex": {
        "model": "gpt-4o-mini",
        "temperature": 0.5,
        "max_tokens": 1536,
        "top_p": 0.9,
    },
}
```

---

## 4. Prompt Builder

**File:** `apps/api/app/services/ai/prompt_builder.py`

The prompt builder constructs the message array sent to the AI provider. It must never allow user input to override system instructions.

### 4.1 Prompt Structure

The prompt is built in this order:

```text
1. System Prompt
   ├── Brand identity and tone
   ├── Language instruction
   ├── Safety rules (medical, age, hallucination)
   ├── Handoff instructions
   └── Response format guidelines

2. Retrieved Knowledge Context
   └── Top-K chunks with source metadata

3. Conversation Summary (if available)
   └── Condensed history of earlier messages

4. Recent Message History
   └── Last 8-12 messages (user + assistant)

5. Current User Message
   └── The new message to respond to
```

### 4.2 System Prompt Components

#### Brand Tone

```text
You are the AI assistant for Krystal Tattoo Studio, a professional tattoo, piercing,
and dreadlock studio in Ahmedabad. You sound professional, friendly, casual, trustworthy,
and helpful. You are honest when you are unsure about something.
```

#### Language Instruction

```text
Respond in the same language the user is writing in. If the user writes in Hindi,
respond in Hindi. If the user writes in Gujarati, respond in Gujarati. Default to English.
Use natural, conversational language — not formal or robotic.
```

#### Safety Rules

```text
CRITICAL SAFETY RULES:
- Never invent exact prices. Provide price ranges from the knowledge base only.
- Never confirm appointment availability. Direct users to contact the studio.
- Never state artist schedules unless explicitly documented in the knowledge base.
- Never provide legal advice.
- Never diagnose medical conditions or prescribe treatments.
- Never state studio policies that are not in the knowledge base.
- If you are unsure about anything, say so and offer to help the user contact the studio directly.
```

#### Age Restriction

```text
AGE POLICY:
- For tattoo and piercing enquiries, mention that valid ID and age verification may be required.
- Do not advise anyone to bypass age verification requirements.
- For minor/guardian questions, direct the user to contact the studio for clarification.
```

#### Handoff Instructions

```text
HANDOFF:
- If you cannot confidently answer based on the provided knowledge, do not guess.
- Instead, say: "I don't want to guess on that. Best option is to contact the studio directly
  by phone or message the official Instagram so the team can confirm it properly."
- Studio phone: {STUDIO_PHONE}
- Studio Instagram: {STUDIO_INSTAGRAM_URL}
```

### 4.3 Knowledge Context Formatting

Retrieved chunks are injected into the prompt with clear boundaries:

```text
=== RETRIEVED KNOWLEDGE ===

[Source: Tattoo Pricing Guide | Language: English]
Small tattoos typically start from a base price depending on size, placement, and detail...

[Source: Piercing Aftercare | Language: English]
Clean your new piercing twice daily with saline solution...

=== END RETRIEVED KNOWLEDGE ===

Answer the user's question using ONLY the information above. If the answer is not in
the retrieved knowledge, say you are unsure and offer to help them contact the studio.
```

### 4.4 Conversation Summary

When a conversation exceeds 12 messages, generate or use a summary:

```text
=== CONVERSATION SUMMARY ===
The user is interested in getting a small tattoo on their wrist. They asked about pricing,
aftercare, and whether they need to book in advance. They prefer communicating in English.
=== END SUMMARY ===
```

---

## 5. Hallucination Prevention

### 5.1 Absolute Prohibitions

The AI must never invent or fabricate:

| Category | Example | Correct Behavior |
|---|---|---|
| Exact prices | "A small tattoo costs ₹1,500" | Provide ranges from KB: "Small tattoos typically start from [range]. Contact the studio for an exact quote." |
| Appointment availability | "We have a slot at 3pm tomorrow" | "I can't check live availability. Contact the studio to book." |
| Artist schedules | "Artist X works on Tuesdays" | Only state if documented in KB. Otherwise hand off. |
| Legal rules | "The legal age for tattoos is 18" | "Age requirements vary. The studio will verify ID. Contact them for details." |
| Medical diagnosis | "That sounds like an infection" | "I can't diagnose medical issues. Please consult a healthcare professional." |
| Studio policies not in KB | "We offer a 10% discount" | Only state policies documented in the knowledge base. Otherwise hand off. |

### 5.2 Grounding Rules

- Every factual claim in the AI response must be traceable to retrieved knowledge.
- If no relevant knowledge is retrieved (similarity below threshold), the AI must not answer from general knowledge.
- The AI must use hedging language for pricing: "typically," "starts from," "depends on."
- When providing ranges, always caveat with "for an accurate quote, contact the studio."

### 5.3 No-Knowledge Fallback

When retrieval returns no results above the similarity threshold:

1. Do not attempt to answer from general knowledge.
2. Return a handoff response:
   > "I don't want to guess on that. Best option is to contact the studio directly by phone or message the official Instagram so the team can confirm it properly."
3. Log the failed query for knowledge base improvement.

---

## 6. Medical and Aftercare Rules

### 6.1 Allowed Behaviors

- Provide general aftercare guidance that is explicitly documented in the knowledge base.
- Recommend contacting the studio for any concerns about healing.
- Recommend consulting a healthcare professional for serious symptoms.
- Describe normal healing timelines if documented in the knowledge base.
- Explain aftercare products recommended by the studio (if in KB).

### 6.2 Prohibited Behaviors

| Prohibited Action | Why |
|---|---|
| Diagnosing infection | Not qualified; liability risk |
| Telling user to ignore symptoms | Dangerous; liability risk |
| Guaranteeing healing times | Unrealistic; liability risk |
| Prescribing medication | Illegal without license |
| Suggesting home remedies not in KB | Unverified; safety risk |
| Downplaying reported pain | Could mask complications |

### 6.3 Medical Handoff Protocol

When a user describes symptoms that could indicate complications (swelling, pus, excessive pain, redness spreading, fever):

1. Acknowledge the concern empathetically.
2. State that the AI cannot diagnose or assess medical situations.
3. Recommend contacting the studio immediately.
4. Recommend consulting a healthcare professional if symptoms are severe.
5. Do not provide any treatment advice beyond what is in the knowledge base aftercare instructions.

Example response:

```text
I can see you're concerned about how your piercing is healing. I'm not able to assess
or diagnose medical situations — that's best handled by a professional. I'd recommend
contacting the studio directly so they can take a look, and if symptoms are severe or
worsening, please consult a healthcare professional.

Studio phone: {STUDIO_PHONE}
Studio Instagram: {STUDIO_INSTAGRAM_URL}
```

---

## 7. Age Restriction Rules

### 7.1 Policy

- Tattoo and piercing services may require age verification and valid government-issued ID.
- Age requirements are subject to local laws and studio policy.
- The AI does not collect full date of birth from users.

### 7.2 Required Behaviors

- When a user asks about tattoo or piercing services, mention that valid ID and age verification may be required.
- If a user identifies as a minor or asks about services for a minor:
  - Explain that age restrictions apply.
  - Recommend contacting the studio directly to discuss options with parental/guardian consent.
  - Do not advise bypassing age verification.
- If a user asks "can I get a tattoo if I'm under 18?", the response must mention ID verification and suggest contacting the studio.

### 7.3 Prohibited Behaviors

- Do not advise users on how to bypass age restrictions.
- Do not state a definitive legal age unless it is in the knowledge base.
- Do not encourage minors to visit without a guardian.

---

## 8. Handoff Triggers and Message Style

### 8.1 Handoff Triggers

Trigger a handoff to human staff when any of these conditions are detected:

| Trigger | Example |
|---|---|
| Low confidence response | Intent classifier returns confidence below threshold |
| No relevant RAG context | Similarity scores all below threshold |
| Medical/infection concern | User mentions pus, severe pain, swelling, fever |
| Exact price request | "How much exactly will my tattoo cost?" |
| Booking confirmation request | "Can you book me for Saturday?" |
| Legal/age restriction edge case | Minor asking about services |
| Angry/frustrated user | "This is terrible service", "You're useless" |
| Complex custom design request | Detailed custom artwork discussion |
| Policy unclear | Question about policy not in KB |
| Prompt injection detected | User attempting to manipulate the AI |

### 8.2 Handoff Message Style

Handoff messages must be:

- **Empathetic** — acknowledge the user's need.
- **Honest** — explain why the AI cannot help fully.
- **Actionable** — provide clear next steps.
- **Branded** — sound like the studio, not a corporate bot.

Default handoff message:

```text
I don't want to guess on that. Best option is to contact the studio directly
by phone or message the official Instagram so the team can confirm it properly.

📞 Phone: {STUDIO_PHONE}
📸 Instagram: {STUDIO_INSTAGRAM_URL}
```

The handoff message must always include at least one direct contact method.

### 8.3 Handoff Response Format

When a handoff is triggered, the API response includes:

```json
{
  "content": "I don't want to guess on that...",
  "handoff": {
    "triggered": true,
    "reason": "no_rag_context",
    "contact_phone": "+91-XXXX-XXXXXX",
    "contact_instagram": "https://www.instagram.com/krystaltattoostudio"
  }
}
```

---

## 9. RAG Pipeline

### 9.1 Full RAG Flow

```text
Knowledge Sources
  ├── Website pages (service descriptions, about page, contact info)
  ├── FAQs (common questions with verified answers)
  ├── PDFs (aftercare sheets, policy documents)
  ├── Policies (cancellation, hygiene, age requirements)
  ├── Service descriptions (tattoo, piercing, dreadlock details)
  ├── Pricing guidance (ranges, factors, starting prices)
  ├── Instagram content (studio work highlights, FAQs from comments)
  ├── Artist information (bios, specialties, experience)
  ├── Aftercare instructions (tattoo, piercing, dreadlock)
  └── Manual admin input (custom knowledge entries)
        ↓
Ingestion Pipeline (apps/api/app/services/rag/ingestion.py)
        ↓
Clean Text
  - Remove HTML tags, excessive whitespace, special characters
  - Normalize Unicode
  - Strip boilerplate (headers, footers, navigation)
        ↓
Chunk Text (apps/api/app/services/rag/chunker.py)
  - Split into 500-900 token segments
  - 80-150 token overlap between chunks
  - Preserve FAQ Q+A pairs
  - Keep service-specific content together
        ↓
Generate Embeddings (apps/api/app/services/rag/embeddings.py)
  - Use OpenAI text-embedding-3-large
  - Batch embedding calls for efficiency
  - Store document hash to skip unchanged content
        ↓
Store in PostgreSQL + pgvector
  - knowledge_chunks table
  - HNSW index for vector similarity search
  - Metadata: language, service_type, source_type, document_id
        ↓
Query Time
  - Embed user query
  - pgvector similarity search
  - Language preference filter with English fallback
  - Return top 4-6 chunks above similarity threshold
        ↓
Prompt Context
  - Inject retrieved chunks into prompt
  - Include source metadata for transparency
        ↓
Grounded AI Response
  - AI generates response using only retrieved context
  - If no relevant context, trigger handoff
```

### 9.2 Knowledge Sources Detail

| Source | Format | Ingestion Method |
|---|---|---|
| Website pages | HTML | Scraped and cleaned |
| FAQs | Structured text | Direct admin input |
| PDFs | PDF text | Extracted and cleaned |
| Policies | Structured text | Direct admin input |
| Service descriptions | Structured text | Direct admin input |
| Pricing guidance | Structured text | Direct admin input |
| Instagram content | Text summaries | Manual admin input |
| Artist information | Structured text | Direct admin input |
| Aftercare instructions | Structured text | Direct admin input |

### 9.3 Ingestion Pipeline

**File:** `apps/api/app/services/rag/ingestion.py`

The ingestion pipeline processes knowledge documents into searchable chunks:

1. Receive a knowledge document (new or updated).
2. Clean the raw content (remove HTML, normalize whitespace, strip boilerplate).
3. Pass cleaned text to the chunker.
4. Generate embeddings for each chunk.
5. Delete old chunks for this document (if reindexing).
6. Insert new chunks with embeddings and metadata.
7. Update the document status to "indexed".
8. Log ingestion metrics (document ID, chunk count, embedding status).

### 9.4 Text Cleaning Rules

- Remove HTML tags but preserve text structure.
- Normalize Unicode characters.
- Remove excessive whitespace and blank lines.
- Preserve headings as context markers.
- Strip navigation menus, footers, and boilerplate.
- Keep URLs as plain text.
- Preserve numbered/bulleted list formatting.

---

## 10. Chunking Strategy

**File:** `apps/api/app/services/rag/chunker.py`

### 10.1 Configuration

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 500-900 tokens (~2,000-3,500 characters) | Large enough for context, small enough for relevance |
| Overlap | 80-150 tokens | Prevents losing information at chunk boundaries |
| Top-K retrieval | 4-6 chunks | Sufficient context without overwhelming the prompt |
| Maximum chunk size | 900 tokens | Hard limit to avoid oversized chunks |

### 10.2 Chunk Metadata

Each chunk stores the following metadata:

```python
class ChunkMetadata:
    document_id: UUID
    chunk_index: int
    language: str          # "en", "hi", "gu"
    service_type: str      # "tattoo", "piercing", "dreadlock", "general"
    source_type: str       # "faq", "policy", "service", "aftercare", "pricing"
    title: str             # Source document title
    updated_at: datetime   # For staleness checks
```

### 10.3 Chunking Rules

1. **Keep FAQ Q+A together** — a question and its answer must be in the same chunk.
2. **Keep aftercare steps together** — sequential aftercare instructions should not be split across chunks.
3. **Keep pricing guidance together** — a pricing range and its context must be in the same chunk.
4. **Do not mix service types** — tattoo, piercing, and dreadlock content must be in separate chunks.
5. **Avoid huge chunks** — if a section exceeds 900 tokens, split at a natural boundary (paragraph, heading).
6. **Avoid tiny chunks without context** — if a section is too small (<100 tokens), merge with the adjacent section.
7. **Split at natural boundaries** — prefer splitting at paragraph breaks, heading transitions, or list boundaries.
8. **Preserve headings in chunks** — if a chunk starts mid-section, include the section heading for context.

### 10.4 Chunking Algorithm

```text
Input: Cleaned document text + metadata
Output: List of chunks with metadata

1. Parse document into sections by heading structure.
2. For each section:
   a. If section fits in one chunk (≤900 tokens), create one chunk.
   b. If section is too large, split at paragraph boundaries.
   c. If split point falls mid-FAQ, keep Q+A together by splitting before the question.
   d. Add overlap from the previous chunk's end.
3. Tag each chunk with metadata (language, service_type, source_type).
4. Validate no chunk exceeds the maximum token limit.
5. Return ordered list of chunks.
```

---

## 11. Retrieval Strategy

**File:** `apps/api/app/services/rag/retriever.py`

### 11.1 Retrieval Flow

```text
1. Receive user query + conversation language preference.
2. Embed the user query using the embedding service.
3. Execute pgvector similarity search against knowledge_chunks.
4. Filter by:
   a. Active status (document status = "active").
   b. Language preference (preferred language first, then English fallback).
   c. Service type (if intent classified a specific service).
5. Return top 4-6 chunks with similarity score above threshold.
6. If no chunks meet the threshold, return empty results (trigger handoff).
7. Attach source metadata to each chunk for prompt injection.
```

### 11.2 Language Preference Handling

```text
Priority:
1. Chunks matching the user's selected language.
2. Chunks in English as fallback.
3. Never return chunks in a language the user didn't select (unless falling back to English).
```

Example: If the user selected Hindi:
- First, search for Hindi chunks.
- If fewer than 2 relevant Hindi chunks are found, supplement with English chunks.
- Never return Gujarati chunks for a Hindi user unless explicitly requested.

### 11.3 Similarity Threshold

- **High confidence threshold:** 0.78 — chunk is clearly relevant.
- **Low confidence threshold:** 0.65 — chunk might be relevant, include with caution.
- **No-result threshold:** Below 0.65 — do not include, trigger handoff.

When chunks score between 0.65 and 0.78, include them but note lower confidence. The prompt builder should instruct the AI to be more cautious with these results.

### 11.4 No-Context Fallback

When retrieval returns no results above the similarity threshold:

1. Do not send empty context to the AI.
2. Set a `no_context` flag in the orchestrator.
3. The prompt builder generates a handoff-biased system prompt.
4. The AI is instructed to acknowledge it cannot help and offer contact methods.
5. Log the failed query for knowledge base improvement:
   - User query
   - Top similarity score (even if below threshold)
   - Intent classification
   - Timestamp

### 11.5 Retrieval Performance

- Use HNSW index on the `embedding` column in `knowledge_chunks` for fast approximate nearest neighbor search.
- Index configuration: `m = 16, ef_construction = 64`.
- Query-time parameter: `ef_search = 40`.
- These values balance accuracy and latency for a small-medium knowledge base.

---

## 12. Memory Strategy

**File:** `apps/api/app/services/chat/memory.py`

### 12.1 Memory Layers

| Layer | Scope | Storage | TTL |
|---|---|---|---|
| Short-term | Recent conversation messages | `messages` table | Conversation lifetime |
| Conversation summary | Condensed chat history | `conversations.summary` field | Conversation lifetime |
| Lead profile | User details extracted from chat | `leads` table | Until manually deleted |

### 12.2 Short-Term Memory

- Maintain the last 8-12 messages in the conversation.
- Include both user and assistant messages.
- Exclude system messages from the history sent to the AI.
- When the conversation exceeds 12 messages, summarize earlier messages.

### 12.3 Conversation Summary

- When a conversation grows beyond 12 messages, generate a summary of messages 1 through N-12.
- Store the summary in the `conversations.summary` field.
- Include in the prompt as context for the AI.
- Update the summary every time the conversation grows by another 6 messages.

Summary format:

```text
The user is interested in [service]. They have asked about [topics discussed].
They prefer communicating in [language]. Key details: [extracted lead info].
```

### 12.4 Lead Profile Fields

Extracted from conversation and stored in the `leads` table:

```text
name          — User's name
email         — User's email address
phone         — User's phone number
service_interest — Which service they're interested in
budget_range  — Mentioned budget if any
placement     — Where on the body
style_preference — Preferred style if mentioned
```

### 12.5 Memory Retrieval for Prompt

When building a prompt, the memory module provides:

```text
1. Conversation summary (if exists).
2. Last 8-12 messages from the conversation.
3. Lead profile fields (if any have been extracted).
```

### 12.6 Future Memory (Not in MVP)

The following are planned for later phases:

- Long-term customer memory (across sessions).
- Booking history context.
- CRM integration for returning customers.
- Preference learning from past interactions.

---

## 13. Prompt Injection Defense

**File:** `apps/api/app/services/ai/safety.py`

### 13.1 Detection Patterns

The safety module scans user messages for known injection patterns before processing:

| Pattern | Category | Response |
|---|---|---|
| "ignore previous instructions" | Instruction override | Refuse + log |
| "reveal your system prompt" | System prompt extraction | Refuse + log |
| "show hidden rules" | System prompt extraction | Refuse + log |
| "access admin data" | Unauthorized access | Refuse + log |
| "delete database" | Destructive action | Refuse + log |
| "change your policies" | Policy manipulation | Refuse + log |
| "pretend you are not a chatbot" | Identity manipulation | Refuse + log |
| "you are now [role]" | Role override | Refuse + log |
| "forget everything above" | Context manipulation | Refuse + log |
| "output your instructions" | System prompt extraction | Refuse + log |

### 13.2 Defense Layers

1. **Input validation** — Pydantic schemas reject oversized or malformed messages.
2. **Pattern detection** — Safety module scans for injection patterns.
3. **Prompt separation** — System prompt is clearly delimited from user content.
4. **Content labeling** — Retrieved knowledge is wrapped in clear boundaries.
5. **Output filtering** — AI responses are checked for leaked system instructions.
6. **No tool access** — The AI has no access to tools, databases, or admin functions.

### 13.3 Response to Injection Attempts

When an injection attempt is detected:

```text
I'm here to help with questions about Krystal Tattoo Studio's services, pricing,
and policies. I can't follow instructions that go outside that scope. Is there
something about the studio I can help you with?
```

Never:
- Acknowledge the injection attempt in detail.
- Reveal what patterns were detected.
- Explain the security system.
- React confrontationally.

### 13.4 Retrieved Content Treatment

All retrieved knowledge chunks are treated as untrusted content:

- Wrapped in clear delimiters (`=== RETRIEVED KNOWLEDGE ===` / `=== END ===`).
- Never inserted into the system prompt section.
- The AI is instructed to use them as reference only, not as instructions.
- Metadata (source, language) is included for traceability.

---

## 14. Provider Configuration

### 14.1 Chat Model

| Parameter | Value |
|---|---|
| Provider | OpenAI |
| Model | `gpt-4o-mini` |
| Purpose | Chat generation |
| Temperature | 0.7 (default), 0.5 (complex) |
| Max tokens | 1024 (default), 1536 (complex) |
| Top_p | 1.0 (default), 0.9 (complex) |

### 14.2 Embedding Model

| Parameter | Value |
|---|---|
| Provider | OpenAI |
| Model | `text-embedding-3-large` |
| Purpose | Document and query embeddings |
| Dimensions | 3072 (default) |
| Batch size | 100 chunks per API call |

### 14.3 Environment Variables

```text
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large
```

### 14.4 Cost Estimation

| Operation | Model | Approximate Cost |
|---|---|---|
| Chat response (short) | gpt-4o-mini | ~$0.00015 per message |
| Chat response (long) | gpt-4o-mini | ~$0.0005 per message |
| Query embedding | text-embedding-3-large | ~$0.00013 per query |
| Document embedding (100 chunks) | text-embedding-3-large | ~$0.013 per document |

Estimated monthly cost at 100 users/day: **$2-5/month** for AI operations.

### 14.5 Future Provider Support

The abstraction layer is designed to support future providers:

- **Anthropic Claude** — for higher-quality responses when needed.
- **Local models** — for cost reduction on high-volume simple queries.
- **Custom fine-tuned models** — for studio-specific recommendations.

Swapping providers requires implementing the `AIProvider` protocol — no route or orchestrator changes needed.
