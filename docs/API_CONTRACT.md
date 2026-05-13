# API Contract — Krystal Studio AI Chatbot

> **Source of truth:** This document defines every API endpoint for the Krystal Studio AI Chatbot platform. All implementations must follow these contracts exactly. Read PLAN.md before modifying this file.

---

## 1. General Rules

### 1.1 Base URL

```
Production:  https://{backend-domain}/api/v1
Development: http://localhost:8000/api/v1
```

### 1.2 Content Type

All request and response bodies use `application/json`.

### 1.3 Authentication

| Type | Description |
|------|-------------|
| None | Public endpoints (chat, leads, health, feedback) |
| JWT Bearer | Admin endpoints require `Authorization: Bearer <token>` header |

### 1.4 Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | `application/json` |
| `Authorization` | Admin only | `Bearer <jwt_token>` |
| `X-Request-ID` | Optional | Correlation ID for tracing |

---

## 2. Error Response Format

All errors return a consistent shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error description",
    "details": {}
  }
}
```

### 2.1 Standard Error Codes

| HTTP Status | Error Code | Description |
|-------------|-----------|-------------|
| 400 | `VALIDATION_ERROR` | Request body or parameters failed validation |
| 401 | `UNAUTHENTICATED` | Missing or invalid JWT token |
| 403 | `FORBIDDEN` | Authenticated but insufficient role permissions |
| 404 | `NOT_FOUND` | Requested resource does not exist |
| 409 | `CONFLICT` | Resource already exists or state conflict |
| 429 | `RATE_LIMITED` | Too many requests, try again later |
| 500 | `INTERNAL_ERROR` | Unexpected server error (no stack trace in production) |

---

## 3. Common Schemas

### 3.1 Pagination Parameters (Query)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | 1 | Page number (1-indexed) |
| `page_size` | `integer` | 20 | Items per page (max 100) |

### 3.2 Paginated Response

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "total_pages": 0
}
```

### 3.3 ID Parameter

All `{id}`, `{lead_id}`, `{conversation_id}`, and `{document_id}` path parameters are UUID strings.

---

## 4. Public APIs

### 4.1 Health Check

**`GET /api/v1/health`**

Returns system health status. No authentication required.

**Request:** No body.

**Response (200):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "db": "connected"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"healthy"` or `"degraded"` |
| `version` | `string` | Application version |
| `db` | `string` | `"connected"` or `"disconnected"` |

---

### 4.2 Start Conversation

**`POST /api/v1/chat/start`**

Creates a new conversation session. No authentication required.

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `language` | `string` | No | `"en"` | Preferred language code (`"en"`, `"hi"`, `"gu"`) |
| `metadata` | `object` | No | `null` | Optional client metadata (user agent, referrer) |

```json
{
  "language": "en",
  "metadata": {
    "referrer": "https://krystaltattoostudio.com"
  }
}
```

**Response (200):**

```json
{
  "session_id": "uuid-string",
  "language": "en",
  "welcome_message": "Hey! Welcome to Krystal Tattoo Studio. How can I help you today?",
  "quick_replies": ["Tattoo services", "Piercing info", "Pricing", "Aftercare"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Unique session identifier (UUID) |
| `language` | `string` | Confirmed language code |
| `welcome_message` | `string` | Branded welcome message in the selected language |
| `quick_replies` | `string[]` | Suggested quick-reply options |

---

### 4.3 Send Message

**`POST /api/v1/chat/message`**

Sends a user message and receives an AI response. No authentication required.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | `string` | Yes | Session ID from `/chat/start` |
| `message` | `string` | Yes | User message (1–2000 characters) |
| `language` | `string` | No | Override language for this message |

```json
{
  "session_id": "uuid-string",
  "message": "How much does a small tattoo cost?",
  "language": "en"
}
```

**Response (200):**

```json
{
  "message_id": "uuid-string",
  "response": "The cost of a small tattoo depends on a few things — size, placement, detail level, and the artist's rate. Generally, small tattoos at Krystal Tattoo Studio start from a base price and go up based on complexity. Best to visit the studio for an exact quote!",
  "sources": [
    {
      "document_title": "Tattoo Pricing Guide",
      "chunk_preview": "Small tattoos typically range from..."
    }
  ],
  "intent": "pricing_guidance",
  "confidence": 0.87,
  "handoff": false,
  "lead_capture_suggested": true,
  "quick_replies": ["Book a consultation", "See piercing prices", "Aftercare tips"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | `string` | UUID of the assistant's response message |
| `response` | `string` | Chatbot's reply text |
| `sources` | `object[]` | RAG source references (document_title, chunk_preview) |
| `intent` | `string` | Classified intent (e.g., `pricing_guidance`, `aftercare`, `service_info`) |
| `confidence` | `float` | Confidence score 0.0–1.0 |
| `handoff` | `boolean` | Whether handoff to human is recommended |
| `lead_capture_suggested` | `boolean` | Whether to prompt lead capture form |
| `quick_replies` | `string[]` | Suggested follow-up options |

**Response (200, handoff case):**

```json
{
  "message_id": "uuid-string",
  "response": "I don't want to guess on that. Best option is to contact the studio directly — call +91-XXXX-XXXXXX or message the official Instagram @krystaltattoostudio so the team can confirm it properly.",
  "sources": [],
  "intent": "booking_request",
  "confidence": 0.42,
  "handoff": true,
  "handoff_reason": "booking_confirmation_requested",
  "lead_capture_suggested": true,
  "quick_replies": ["Leave my contact details", "Continue chatting"]
}
```

| Additional Field | Type | Description |
|-----------------|------|-------------|
| `handoff_reason` | `string` | Reason for handoff trigger |

**Status Codes:** 200 (success), 400 (validation error), 404 (session not found), 429 (rate limited)

---

### 4.4 Submit Feedback

**`POST /api/v1/chat/feedback`**

Submits user feedback on a chatbot response. No authentication required.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | `string` | Yes | UUID of the assistant message being rated |
| `rating` | `integer` | Yes | 1 (thumbs down) or 2 (thumbs up) |
| `comment` | `string` | No | Optional text feedback (max 500 characters) |

```json
{
  "message_id": "uuid-string",
  "rating": 1,
  "comment": "The price info was too vague"
}
```

**Response (200):**

```json
{
  "id": "uuid-string",
  "message": "Feedback recorded. Thank you!"
}
```

**Status Codes:** 200 (success), 400 (validation error), 404 (message not found), 429 (rate limited)

---

### 4.5 Create Lead

**`POST /api/v1/leads`**

Creates a new customer lead. No authentication required.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Customer name (1–200 characters) |
| `email` | `string` | No | Customer email (valid email format) |
| `phone` | `string` | No | Customer phone number |
| `preferred_language` | `string` | No | Language code, default `"en"` |
| `service_interest` | `string` | No | Service category (`"tattoo"`, `"piercing"`, `"dreadlock"`) |
| `budget_range` | `string` | No | Customer's budget range |
| `placement` | `string` | No | Desired body placement |
| `style_preference` | `string` | No | Preferred style |
| `notes` | `string` | No | Additional notes |
| `session_id` | `string` | No | Link to conversation session |

```json
{
  "name": "Rahul Patel",
  "email": "rahul@example.com",
  "phone": "+91-98765-43210",
  "preferred_language": "en",
  "service_interest": "tattoo",
  "budget_range": "₹3,000–5,000",
  "placement": "left forearm",
  "style_preference": "realism",
  "notes": "Looking for a portrait tattoo",
  "session_id": "uuid-string"
}
```

**Response (201):**

```json
{
  "id": "uuid-string",
  "name": "Rahul Patel",
  "status": "new",
  "created_at": "2026-05-13T16:00:00Z"
}
```

**Status Codes:** 201 (created), 400 (validation error), 429 (rate limited)

---

## 5. Admin APIs

All admin endpoints require JWT Bearer authentication.

### 5.1 Admin Login

**`POST /api/v1/admin/auth/login`**

Authenticates an admin user and returns JWT tokens.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | `string` | Yes | Admin email address |
| `password` | `string` | Yes | Admin password |

```json
{
  "email": "admin@krystalstudio.com",
  "password": "secure-password"
}
```

**Response (200):**

```json
{
  "access_token": "jwt-token-string",
  "token_type": "bearer",
  "expires_in": 480,
  "user": {
    "id": "uuid-string",
    "email": "admin@krystalstudio.com",
    "role": "owner"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | `string` | JWT access token |
| `token_type` | `string` | Always `"bearer"` |
| `expires_in` | `integer` | Token lifetime in minutes |
| `user.id` | `string` | User UUID |
| `user.email` | `string` | User email |
| `user.role` | `string` | User role (`owner`, `admin`, `staff`) |

**Status Codes:** 200 (success), 401 (invalid credentials), 429 (rate limited)

---

### 5.2 Get Current User

**`GET /api/v1/admin/me`**

Returns the authenticated admin user's profile.

**Auth:** JWT Bearer required.

**Request:** No body.

**Response (200):**

```json
{
  "id": "uuid-string",
  "email": "admin@krystalstudio.com",
  "role": "owner",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Status Codes:** 200 (success), 401 (unauthenticated)

---

### 5.3 List Leads

**`GET /api/v1/admin/leads`**

Returns a paginated list of captured leads.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | 1 | Page number |
| `page_size` | `integer` | 20 | Items per page (max 100) |
| `status` | `string` | None | Filter by lead status (`new`, `contacted`, `consultation_booked`, `converted`, `closed`) |
| `service_interest` | `string` | None | Filter by service (`tattoo`, `piercing`, `dreadlock`) |
| `sort_by` | `string` | `"created_at"` | Sort field (`created_at`, `updated_at`) |
| `sort_order` | `string` | `"desc"` | Sort direction (`asc`, `desc`) |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "name": "Rahul Patel",
      "email": "rahul@example.com",
      "phone": "+91-98765-43210",
      "preferred_language": "en",
      "service_interest": "tattoo",
      "budget_range": "₹3,000–5,000",
      "placement": "left forearm",
      "style_preference": "realism",
      "notes": "Looking for a portrait tattoo",
      "status": "new",
      "source": "chat",
      "created_at": "2026-05-13T16:00:00Z",
      "updated_at": "2026-05-13T16:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.4 Get Lead

**`GET /api/v1/admin/leads/{lead_id}`**

Returns a single lead by ID.

**Auth:** JWT Bearer required (owner, admin, staff).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `lead_id` | `string` | Lead UUID |

**Response (200):**

```json
{
  "id": "uuid-string",
  "name": "Rahul Patel",
  "email": "rahul@example.com",
  "phone": "+91-98765-43210",
  "preferred_language": "en",
  "service_interest": "tattoo",
  "budget_range": "₹3,000–5,000",
  "placement": "left forearm",
  "style_preference": "realism",
  "notes": "Looking for a portrait tattoo",
  "status": "new",
  "source": "chat",
  "conversation_id": "uuid-string",
  "created_at": "2026-05-13T16:00:00Z",
  "updated_at": "2026-05-13T16:00:00Z"
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden), 404 (not found)

---

### 5.5 Update Lead

**`PATCH /api/v1/admin/leads/{lead_id}`**

Updates a lead's status or notes.

**Auth:** JWT Bearer required (owner, admin). Staff can only update `notes`.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `lead_id` | `string` | Lead UUID |

**Request Body (partial update):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | `string` | No | New status (`new`, `contacted`, `consultation_booked`, `converted`, `closed`) |
| `notes` | `string` | No | Updated notes |

```json
{
  "status": "contacted",
  "notes": "Called customer, interested in consultation next week"
}
```

**Response (200):**

```json
{
  "id": "uuid-string",
  "name": "Rahul Patel",
  "email": "rahul@example.com",
  "phone": "+91-98765-43210",
  "preferred_language": "en",
  "service_interest": "tattoo",
  "budget_range": "₹3,000–5,000",
  "placement": "left forearm",
  "style_preference": "realism",
  "notes": "Called customer, interested in consultation next week",
  "status": "contacted",
  "source": "chat",
  "created_at": "2026-05-13T16:00:00Z",
  "updated_at": "2026-05-13T17:30:00Z"
}
```

**Status Codes:** 200 (success), 400 (validation error), 401 (unauthenticated), 403 (forbidden), 404 (not found)

---

### 5.6 List Conversations

**`GET /api/v1/admin/chats`**

Returns a paginated list of conversations.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | 1 | Page number |
| `page_size` | `integer` | 20 | Items per page (max 100) |
| `status` | `string` | None | Filter by status (`active`, `ended`, `handoff`) |
| `language` | `string` | None | Filter by language code |
| `has_lead` | `boolean` | None | Filter by whether a lead was captured |
| `sort_by` | `string` | `"created_at"` | Sort field |
| `sort_order` | `string` | `"desc"` | Sort direction |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "session_id": "uuid-string",
      "language": "en",
      "status": "ended",
      "summary": "Customer asked about tattoo pricing for a small forearm piece",
      "lead_id": "uuid-string",
      "message_count": 8,
      "created_at": "2026-05-13T15:30:00Z",
      "updated_at": "2026-05-13T16:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.7 Get Conversation

**`GET /api/v1/admin/chats/{conversation_id}`**

Returns a single conversation with all its messages.

**Auth:** JWT Bearer required (owner, admin, staff).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | `string` | Conversation UUID |

**Response (200):**

```json
{
  "id": "uuid-string",
  "session_id": "uuid-string",
  "language": "en",
  "status": "ended",
  "summary": "Customer asked about tattoo pricing for a small forearm piece",
  "lead_id": "uuid-string",
  "created_at": "2026-05-13T15:30:00Z",
  "updated_at": "2026-05-13T16:00:00Z",
  "messages": [
    {
      "id": "uuid-string",
      "role": "user",
      "content": "How much does a small tattoo cost?",
      "intent": "pricing_guidance",
      "confidence": 0.91,
      "created_at": "2026-05-13T15:31:00Z"
    },
    {
      "id": "uuid-string",
      "role": "assistant",
      "content": "The cost of a small tattoo depends on...",
      "intent": "pricing_guidance",
      "confidence": 0.87,
      "created_at": "2026-05-13T15:31:05Z"
    }
  ]
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden), 404 (not found)

---

### 5.8 List Knowledge Documents

**`GET /api/v1/admin/knowledge`**

Returns a paginated list of knowledge documents.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | 1 | Page number |
| `page_size` | `integer` | 20 | Items per page (max 100) |
| `status` | `string` | None | Filter by status (`active`, `draft`, `archived`) |
| `language` | `string` | None | Filter by language |
| `source_type` | `string` | None | Filter by source (`manual`, `website`, `pdf`, `faq`) |
| `sort_by` | `string` | `"updated_at"` | Sort field |
| `sort_order` | `string` | `"desc"` | Sort direction |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "title": "Tattoo Pricing Guide",
      "source_type": "manual",
      "source_url": null,
      "language": "en",
      "status": "active",
      "chunk_count": 5,
      "created_at": "2026-05-01T10:00:00Z",
      "updated_at": "2026-05-10T14:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.9 Create Knowledge Document

**`POST /api/v1/admin/knowledge`**

Creates a new knowledge document and triggers ingestion.

**Auth:** JWT Bearer required (owner, admin).

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `string` | Yes | Document title (1–500 characters) |
| `source_type` | `string` | Yes | Source type (`manual`, `website`, `pdf`, `faq`) |
| `source_url` | `string` | No | URL if source is website |
| `language` | `string` | No | Language code, default `"en"` |
| `content` | `string` | Yes | Document content (min 10 characters) |
| `status` | `string` | No | `"active"` or `"draft"`, default `"active"` |
| `metadata` | `object` | No | Additional metadata (service_type, category) |

```json
{
  "title": "Tattoo Aftercare Guide",
  "source_type": "manual",
  "language": "en",
  "content": "Proper aftercare is essential for a healing tattoo...",
  "status": "active",
  "metadata": {
    "service_type": "tattoo",
    "category": "aftercare"
  }
}
```

**Response (201):**

```json
{
  "id": "uuid-string",
  "title": "Tattoo Aftercare Guide",
  "source_type": "manual",
  "source_url": null,
  "language": "en",
  "content": "Proper aftercare is essential for a healing tattoo...",
  "status": "active",
  "chunk_count": 0,
  "metadata_json": {
    "service_type": "tattoo",
    "category": "aftercare"
  },
  "created_at": "2026-05-13T16:00:00Z",
  "updated_at": "2026-05-13T16:00:00Z"
}
```

**Status Codes:** 201 (created), 400 (validation error), 401 (unauthenticated), 403 (forbidden)

---

### 5.10 Get Knowledge Document

**`GET /api/v1/admin/knowledge/{document_id}`**

Returns a single knowledge document with full content.

**Auth:** JWT Bearer required (owner, admin, staff).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | `string` | Document UUID |

**Response (200):**

```json
{
  "id": "uuid-string",
  "title": "Tattoo Aftercare Guide",
  "source_type": "manual",
  "source_url": null,
  "language": "en",
  "content": "Full document content here...",
  "status": "active",
  "chunk_count": 5,
  "metadata_json": {
    "service_type": "tattoo",
    "category": "aftercare"
  },
  "created_at": "2026-05-13T16:00:00Z",
  "updated_at": "2026-05-13T16:00:00Z"
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden), 404 (not found)

---

### 5.11 Update Knowledge Document

**`PATCH /api/v1/admin/knowledge/{document_id}`**

Updates a knowledge document. Changing `content` or `status` to `active` does not auto-reindex — use the reindex endpoint.

**Auth:** JWT Bearer required (owner, admin).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | `string` | Document UUID |

**Request Body (partial update):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `string` | No | Updated title |
| `content` | `string` | No | Updated content |
| `status` | `string` | No | Updated status |
| `language` | `string` | No | Updated language |
| `metadata` | `object` | No | Updated metadata |

```json
{
  "content": "Updated aftercare instructions...",
  "status": "active"
}
```

**Response (200):**

```json
{
  "id": "uuid-string",
  "title": "Tattoo Aftercare Guide",
  "source_type": "manual",
  "source_url": null,
  "language": "en",
  "content": "Updated aftercare instructions...",
  "status": "active",
  "chunk_count": 5,
  "metadata_json": {},
  "created_at": "2026-05-13T16:00:00Z",
  "updated_at": "2026-05-13T17:00:00Z"
}
```

**Status Codes:** 200 (success), 400 (validation error), 401 (unauthenticated), 403 (forbidden), 404 (not found)

---

### 5.12 Delete Knowledge Document

**`DELETE /api/v1/admin/knowledge/{document_id}`**

Deletes a knowledge document and all its chunks.

**Auth:** JWT Bearer required (owner only).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | `string` | Document UUID |

**Response (200):**

```json
{
  "message": "Document deleted successfully",
  "id": "uuid-string"
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden — owner only), 404 (not found)

---

### 5.13 Reindex Knowledge Document

**`POST /api/v1/admin/knowledge/{document_id}/reindex`**

Re-chunks and re-embeds a knowledge document. Deletes old chunks first.

**Auth:** JWT Bearer required (owner, admin).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | `string` | Document UUID |

**Request:** No body.

**Response (200):**

```json
{
  "document_id": "uuid-string",
  "status": "indexed",
  "chunk_count": 6,
  "message": "Document reindexed successfully"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | `string` | Document UUID |
| `status` | `string` | `"indexed"` or `"failed"` |
| `chunk_count` | `integer` | Number of chunks created |
| `message` | `string` | Status message |

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden), 404 (not found), 500 (indexing failed)

---

### 5.14 Analytics Overview

**`GET /api/v1/admin/analytics/overview`**

Returns high-level analytics for a date range.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `string` | 30 days ago | Start date (ISO 8601) |
| `end_date` | `string` | Today | End date (ISO 8601) |

**Response (200):**

```json
{
  "period": {
    "start_date": "2026-04-13",
    "end_date": "2026-05-13"
  },
  "total_conversations": 320,
  "total_messages": 1840,
  "total_leads": 45,
  "lead_conversion_rate": 0.14,
  "handoff_rate": 0.18,
  "average_feedback_rating": 1.7,
  "popular_services": [
    {"service": "tattoo", "count": 180},
    {"service": "piercing", "count": 95},
    {"service": "dreadlock", "count": 45}
  ],
  "language_distribution": [
    {"language": "en", "count": 210},
    {"language": "hi", "count": 75},
    {"language": "gu", "count": 35}
  ]
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.15 Popular Intents

**`GET /api/v1/admin/analytics/popular-intents`**

Returns the most frequent conversation intents.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `string` | 30 days ago | Start date (ISO 8601) |
| `end_date` | `string` | Today | End date (ISO 8601) |
| `limit` | `integer` | 20 | Max results (max 100) |

**Response (200):**

```json
{
  "period": {
    "start_date": "2026-04-13",
    "end_date": "2026-05-13"
  },
  "intents": [
    {"intent": "pricing_guidance", "count": 85, "percentage": 0.27},
    {"intent": "service_info", "count": 62, "percentage": 0.19},
    {"intent": "aftercare", "count": 48, "percentage": 0.15},
    {"intent": "recommendation", "count": 35, "percentage": 0.11}
  ]
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.16 Failed Queries

**`GET /api/v1/admin/analytics/failed-queries`**

Returns queries where the chatbot had low confidence or triggered handoff.

**Auth:** JWT Bearer required (owner, admin, staff).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `string` | 30 days ago | Start date (ISO 8601) |
| `end_date` | `string` | Today | End date (ISO 8601) |
| `page` | `integer` | 1 | Page number |
| `page_size` | `integer` | 20 | Items per page (max 100) |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid-string",
      "conversation_id": "uuid-string",
      "user_message": "Can you book me an appointment for Friday?",
      "intent": "booking_request",
      "confidence": 0.35,
      "handoff_triggered": true,
      "handoff_reason": "booking_confirmation_requested",
      "created_at": "2026-05-13T15:45:00Z"
    }
  ],
  "total": 58,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.17 Get Settings

**`GET /api/v1/admin/settings`**

Returns current chatbot and studio settings.

**Auth:** JWT Bearer required (owner, admin).

**Response (200):**

```json
{
  "studio_name": "Krystal Tattoo Studio",
  "studio_phone": "+91-XXXX-XXXXXX",
  "studio_instagram": "https://www.instagram.com/krystaltattoostudio",
  "studio_address": "2nd floor, Signature Arcade, 203, Gangotri Cir Rd, Nikol, Ahmedabad, Gujarat 382350",
  "studio_hours": {
    "mon_sat": "11:30 am - 10 pm",
    "sun": "12 - 10 pm"
  },
  "default_language": "en",
  "supported_languages": ["en", "hi", "gu"],
  "handoff_message_template": "I don't want to guess on that...",
  "rag_similarity_threshold": 0.7,
  "rag_top_k": 5,
  "max_message_length": 2000,
  "updated_at": "2026-05-13T16:00:00Z"
}
```

**Status Codes:** 200 (success), 401 (unauthenticated), 403 (forbidden)

---

### 5.18 Update Settings

**`PATCH /api/v1/admin/settings`**

Updates chatbot and studio settings.

**Auth:** JWT Bearer required (owner only).

**Request Body (partial update):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `studio_phone` | `string` | No | Updated phone |
| `handoff_message_template` | `string` | No | Updated handoff message |
| `rag_similarity_threshold` | `float` | No | Similarity threshold (0.0–1.0) |
| `rag_top_k` | `integer` | No | Number of chunks to retrieve (1–20) |
| `max_message_length` | `integer` | No | Max user message length (100–5000) |

```json
{
  "rag_similarity_threshold": 0.75,
  "rag_top_k": 6
}
```

**Response (200):**

```json
{
  "studio_name": "Krystal Tattoo Studio",
  "studio_phone": "+91-XXXX-XXXXXX",
  "studio_instagram": "https://www.instagram.com/krystaltattoostudio",
  "studio_address": "2nd floor, Signature Arcade, 203, Gangotri Cir Rd, Nikol, Ahmedabad, Gujarat 382350",
  "studio_hours": {
    "mon_sat": "11:30 am - 10 pm",
    "sun": "12 - 10 pm"
  },
  "default_language": "en",
  "supported_languages": ["en", "hi", "gu"],
  "handoff_message_template": "I don't want to guess on that...",
  "rag_similarity_threshold": 0.75,
  "rag_top_k": 6,
  "max_message_length": 2000,
  "updated_at": "2026-05-13T17:00:00Z"
}
```

**Status Codes:** 200 (success), 400 (validation error), 401 (unauthenticated), 403 (forbidden — owner only)

---

## 6. API Endpoint Summary

### Public Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | None | System health check |
| POST | `/api/v1/chat/start` | None | Start a new conversation |
| POST | `/api/v1/chat/message` | None | Send message, get AI response |
| POST | `/api/v1/chat/feedback` | None | Submit feedback on a response |
| POST | `/api/v1/leads` | None | Create a customer lead |

### Admin Endpoints

| Method | Path | Auth | Min Role | Description |
|--------|------|------|----------|-------------|
| POST | `/api/v1/admin/auth/login` | None | — | Admin login |
| GET | `/api/v1/admin/me` | JWT | staff | Get current user |
| GET | `/api/v1/admin/leads` | JWT | staff | List leads |
| GET | `/api/v1/admin/leads/{lead_id}` | JWT | staff | Get single lead |
| PATCH | `/api/v1/admin/leads/{lead_id}` | JWT | admin | Update lead |
| GET | `/api/v1/admin/chats` | JWT | staff | List conversations |
| GET | `/api/v1/admin/chats/{conversation_id}` | JWT | staff | Get conversation + messages |
| GET | `/api/v1/admin/knowledge` | JWT | staff | List knowledge documents |
| POST | `/api/v1/admin/knowledge` | JWT | admin | Create knowledge document |
| GET | `/api/v1/admin/knowledge/{document_id}` | JWT | staff | Get knowledge document |
| PATCH | `/api/v1/admin/knowledge/{document_id}` | JWT | admin | Update knowledge document |
| DELETE | `/api/v1/admin/knowledge/{document_id}` | JWT | owner | Delete knowledge document |
| POST | `/api/v1/admin/knowledge/{document_id}/reindex` | JWT | admin | Reindex knowledge document |
| GET | `/api/v1/admin/analytics/overview` | JWT | staff | Analytics overview |
| GET | `/api/v1/admin/analytics/popular-intents` | JWT | staff | Popular intents |
| GET | `/api/v1/admin/analytics/failed-queries` | JWT | staff | Failed queries |
| GET | `/api/v1/admin/settings` | JWT | admin | Get settings |
| PATCH | `/api/v1/admin/settings` | JWT | owner | Update settings |

---

## 7. Rate Limiting

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Public chat (`/chat/*`) | 30 requests | per minute per IP |
| Public leads (`/leads`) | 5 requests | per minute per IP |
| Admin login (`/admin/auth/login`) | 10 requests | per minute per IP |
| Admin APIs | 100 requests | per minute per token |
