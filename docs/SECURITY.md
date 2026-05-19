# Security Implementation Plan

> **Read README.md and docs/ARCHITECTURE.md before making changes to security-related code.**
>
> This document covers all MVP security requirements for the KrystalStudio AI chatbot platform. Every item listed here must be implemented before production launch.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Authorization and RBAC](#2-authorization-and-rbac)
3. [CORS Configuration](#3-cors-configuration)
4. [Input Validation](#4-input-validation)
5. [Rate Limiting](#5-rate-limiting)
6. [Secret Management](#6-secret-management)
7. [Logging and PII](#7-logging-and-pii)
8. [Prompt Injection Defense](#8-prompt-injection-defense)
9. [Database Security](#9-database-security)
10. [Privacy and GDPR](#10-privacy-and-gdpr)
11. [API Security Rules](#11-api-security-rules)
12. [Production Security](#12-production-security)

---

## 1. Authentication

### 1.1 JWT Admin Authentication

**Implementation:** `apps/api/app/core/security.py`

All admin endpoints require JWT-based authentication:

- **Algorithm:** HS256 (configurable via `JWT_ALGORITHM` env var).
- **Secret:** Loaded from `JWT_SECRET` environment variable.
- **Token expiry:** Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes).
- **Token format:** Bearer token in `Authorization` header.

**Login flow:**

```text
1. Admin submits email + password to POST /api/v1/admin/auth/login.
2. Server verifies email exists in users table.
3. Server verifies password hash using bcrypt.
4. Server generates JWT with payload: { sub: user_id, role: user_role, exp: expiry }.
5. Server returns { access_token, token_type: "bearer" }.
6. Client includes token in Authorization header for subsequent requests.
```

**Token payload:**

```json
{
  "sub": "user-uuid",
  "email": "admin@krystaltattoo.com",
  "role": "owner",
  "exp": 1715673600,
  "iat": 1715670000
}
```

### 1.2 Password Hashing

**Library:** `passlib[bcrypt]`

- Use `passlib.context.CryptContext` with bcrypt scheme.
- Hash passwords on user creation and password update.
- Verify passwords using `verify(plain, hashed)`.
- Minimum password length: 8 characters.
- Never log, store, or expose plain-text passwords.
- Never return password hashes in API responses.

### 1.3 Admin Route Protection

**Implementation:** `apps/api/app/api/deps.py`

All admin routes use a FastAPI dependency that:

1. Extracts the `Authorization: Bearer <token>` header.
2. Decodes and validates the JWT.
3. Checks token expiry.
4. Loads the user from the database.
5. Attaches the user to the request context.
6. Returns 401 if any step fails.

```python
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """Decode JWT, validate, and return the authenticated user."""
    ...
```

Unauthenticated requests to admin endpoints receive:

```json
{
  "detail": "Not authenticated",
  "status_code": 401
}
```

---

## 2. Authorization and RBAC

### 2.1 Role Definitions

| Role | Access Level |
|---|---|
| `owner` | Full access: all admin APIs, settings, user management, data export/delete |
| `admin` | Most admin APIs: knowledge, leads, chats, analytics; no user management |
| `staff` | Read-only: view leads, chats, knowledge; no edit/delete |

### 2.2 Role Check Implementation

**File:** `apps/api/app/api/deps.py`

```python
def require_role(*allowed_roles: str):
    """Dependency factory that checks if the current user has one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

### 2.3 Endpoint Authorization Matrix

| Endpoint | owner | admin | staff | Public |
|---|---|---|---|---|
| POST /admin/auth/login | Yes | Yes | Yes | Yes |
| GET /admin/me | Yes | Yes | Yes | No |
| GET /admin/leads | Yes | Yes | Yes | No |
| PATCH /admin/leads/{id} | Yes | Yes | No | No |
| DELETE /admin/leads/{id} | Yes | No | No | No |
| GET /admin/chats | Yes | Yes | Yes | No |
| GET /admin/knowledge | Yes | Yes | Yes | No |
| POST /admin/knowledge | Yes | Yes | No | No |
| PATCH /admin/knowledge/{id} | Yes | Yes | No | No |
| DELETE /admin/knowledge/{id} | Yes | Yes | No | No |
| POST /admin/knowledge/{id}/reindex | Yes | Yes | No | No |
| GET /admin/analytics/* | Yes | Yes | Yes | No |
| GET /admin/settings | Yes | Yes | No | No |
| PATCH /admin/settings | Yes | No | No | No |
| POST /chat/message | — | — | — | Yes |
| POST /leads | — | — | — | Yes |

### 2.4 Object-Level Authorization

- Users can only access data within their role's permissions.
- `staff` users can view but not modify knowledge documents.
- `staff` users can view but not update lead statuses.
- `owner` is the only role that can delete leads and manage settings.
- All authorization checks happen server-side. Frontend hides UI elements for unauthorized actions but does not enforce access control.

---

## 3. CORS Configuration

### 3.1 Allowed Origins

**Development:**

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

**Production:**

```python
CORS_ORIGINS = [
    "https://krystaltattoostudio.com",
    "https://www.krystaltattoostudio.com",
]
```

### 3.2 CORS Rules

- Origins are loaded from the `CORS_ORIGINS` environment variable (comma-separated).
- Allow methods: `GET`, `POST`, `PATCH`, `DELETE`, `OPTIONS`.
- Allow headers: `Authorization`, `Content-Type`.
- Allow credentials: `True` (needed for auth).
- Max age: 3600 seconds (preflight cache).
- Never use `*` as allowed origin in production.
- Never allow arbitrary origins.

### 3.3 Implementation

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
```

---

## 4. Input Validation

### 4.1 Pydantic Schema Validation

All request bodies are validated through Pydantic schemas:

- Every endpoint has a defined request schema.
- Invalid data returns 422 with clear error messages.
- String fields have maximum length constraints.
- Email fields use Pydantic's `EmailStr`.
- Enum fields use `str` + `Literal` for allowed values.
- Numeric fields have range constraints where applicable.

### 4.2 Common Validation Rules

| Field | Validation |
|---|---|
| Email | Valid email format, max 254 characters |
| Phone | E.164 or local format, max 20 characters |
| Name | Non-empty, max 100 characters |
| Message content | Non-empty, max 2000 characters |
| Knowledge title | Non-empty, max 200 characters |
| Knowledge content | Non-empty, max 50,000 characters |
| Lead notes | Max 2000 characters |

### 4.3 Request Size Limits

- Maximum request body size: 100KB.
- Maximum message length: 2000 characters.
- Maximum knowledge document content: 50,000 characters.
- Reject oversized requests with 413 status.

---

## 5. Rate Limiting

### 5.1 Implementation

**File:** `apps/api/app/core/rate_limit.py`

Use an in-memory sliding window rate limiter for MVP. Upgrade to Redis-backed if needed.

### 5.2 Rate Limit Rules

| Endpoint | Limit | Window | Key |
|---|---|---|---|
| POST /chat/message | 20 requests | 1 minute | IP address |
| POST /chat/start | 10 requests | 1 minute | IP address |
| POST /admin/auth/login | 5 attempts | 1 minute | IP address |
| POST /leads | 5 requests | 1 minute | IP address |
| GET /admin/* | 60 requests | 1 minute | Authenticated user ID |

### 5.3 Rate Limit Response

When a rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "status_code": 429
}
```

Include `Retry-After` header with seconds until the limit resets.

### 5.4 Rate Limit Headers

All rate-limited responses include:

```text
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1715673600
Retry-After: 45
```

---

## 6. Secret Management

### 6.1 Environment Variables

All secrets are loaded from environment variables:

```text
DATABASE_URL          — PostgreSQL connection string
JWT_SECRET            — Secret key for JWT signing
OPENAI_API_KEY        — OpenAI API key
CORS_ORIGINS          — Allowed CORS origins
STUDIO_PHONE          — Studio phone number
STUDIO_INSTAGRAM_URL  — Studio Instagram URL
```

### 6.2 Frontend Restrictions

The frontend must **never** contain:

- AI API keys (OpenAI, etc.)
- Database credentials
- JWT secrets
- Admin passwords
- Internal API URLs

Only these variables are exposed to the frontend:

```text
NEXT_PUBLIC_API_URL       — Backend API base URL
NEXT_PUBLIC_STUDIO_NAME   — Studio display name
```

### 6.3 `.env` File Rules

- `.env` files are gitignored and never committed.
- `.env.example` files are committed with placeholder values.
- Production secrets are configured through hosting platform dashboards (Railway, Vercel).
- Never hardcode secrets in source code.
- Never log secrets.

---

## 7. Logging and PII

### 7.1 PII-Safe Logging

**Implementation:** `apps/api/app/core/logging.py`

Structured JSON logging with PII sanitization:

```python
def sanitize_log_data(data: dict) -> dict:
    """Remove or mask PII before logging."""
    sensitive_keys = {"password", "token", "api_key", "email", "phone", "name"}
    return {
        k: "***" if k in sensitive_keys else v
        for k, v in data.items()
    }
```

### 7.2 What to Log

| Include | Exclude |
|---|---|
| Request ID | Passwords |
| Endpoint path | JWT tokens |
| HTTP status code | API keys |
| Response latency | Full email addresses |
| Error type | Full phone numbers |
| Conversation ID (when safe) | Full user messages (unless debugging) |
| Intent classification | Password hashes |
| Model used | Database URLs with credentials |
| Token counts | |
| Similarity scores | |

### 7.3 Log Levels

| Level | Usage |
|---|---|
| ERROR | Unhandled exceptions, security events, AI provider failures |
| WARNING | Rate limit hits, low-confidence responses, injection attempts |
| INFO | Request/response cycle, admin actions, knowledge updates |
| DEBUG | Detailed RAG retrieval, prompt construction (dev only) |

### 7.4 Production Logging

- Use structured JSON logs.
- Include request ID for tracing.
- Never include stack traces in production error responses (log them internally).
- Never include PII in log output.
- Log rotation and retention configured in hosting platform.

---

## 8. Prompt Injection Defense

### 8.1 Detection Patterns

**File:** `apps/api/app/services/ai/safety.py`

The safety module scans every user message for injection patterns before processing:

| Pattern | Category |
|---|---|
| `ignore previous instructions` | Instruction override |
| `ignore all previous` | Instruction override |
| `reveal your system prompt` | System prompt extraction |
| `show hidden rules` | System prompt extraction |
| `show your instructions` | System prompt extraction |
| `access admin data` | Unauthorized access attempt |
| `delete database` | Destructive action attempt |
| `change your policies` | Policy manipulation |
| `pretend you are not a chatbot` | Identity manipulation |
| `you are now a` | Role override |
| `forget everything` | Context manipulation |
| `output your instructions` | System prompt extraction |
| `what are your rules` | System prompt extraction |
| `repeat the above` | Instruction leakage |

### 8.2 Defense Implementation

```python
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(hidden\s+)?rules",
    r"access\s+admin\s+data",
    r"delete\s+database",
    r"change\s+(your\s+)?policies",
    r"pretend\s+you\s+(are|are\s+not)\s+a",
    r"you\s+are\s+now\s+a",
    r"forget\s+everything",
    r"output\s+(your\s+)?instructions",
]

def detect_injection(message: str) -> bool:
    """Check if a message contains prompt injection patterns."""
    normalized = message.lower().strip()
    return any(re.search(pattern, normalized) for pattern in INJECTION_PATTERNS)
```

### 8.3 Response to Injection

When an injection attempt is detected:

1. Do not process the message through the AI pipeline.
2. Return a safe refusal response.
3. Log the attempt with the IP address and message hash (not the full message).
4. Track as a security analytics event.

Safe refusal response:

```text
I'm here to help with questions about Krystal Tattoo Studio's services, pricing,
and policies. I can't follow instructions that go outside that scope. Is there
something about the studio I can help you with?
```

### 8.4 System Prompt Protection

- System prompts are never included in user-visible responses.
- Retrieved knowledge is clearly delimited from instructions.
- User messages are never concatenated into system-level prompts.
- The AI has no tool access, database access, or admin function access.
- All authorization checks happen server-side, independent of AI responses.

---

## 9. Database Security

### 9.1 Migration Control

- All schema changes go through Alembic migrations.
- Migrations are reviewed before applying to production.
- No auto-destructive operations (`DROP TABLE`, `TRUNCATE`, `DELETE all`).
- Production migrations are run manually with verification.
- Migration rollback must be tested locally before deploying forward.

### 9.2 Query Safety

- All database queries use parameterized statements via SQLAlchemy ORM.
- No raw SQL with string interpolation.
- Input values are never concatenated into queries.
- SQLAlchemy async sessions are used throughout.

### 9.3 Connection Security

- Database URL is stored as an environment variable.
- SSL connection enforced in production.
- Connection pooling with sensible limits.
- Database credentials rotated periodically.

### 9.4 pgvector Security

- Vector embeddings are stored in the same database with the same access controls.
- No separate vector database with separate authentication.
- Embedding values are not exposed through public APIs.

---

## 10. Privacy and GDPR

### 10.1 Data Collection

Only collect what is necessary for the service:

| Data | Purpose | Required |
|---|---|---|
| Name | Lead identification and personalization | Yes (lead form) |
| Email | Lead follow-up | Yes (lead form) |
| Phone | Lead follow-up | No |
| Service interest | Lead routing | Yes (lead form) |
| Budget range | Lead qualification | No |
| Placement | Lead qualification | No |
| Style preference | Lead qualification | No |
| Chat messages | Service improvement, lead extraction | Collected automatically |
| Language preference | Communication | Collected automatically |

### 10.2 Consent Text

Displayed near the lead capture form:

```text
By submitting your details, you agree that Krystal Tattoo Studio can contact you
about your enquiry. Your information is stored securely and will not be shared with
third parties. You can request deletion of your data at any time by contacting the studio.
```

### 10.3 GDPR Compliance

**Data minimization:**

- Collect only what is needed for the stated purpose.
- Do not collect date of birth, address, or financial information.
- Do not collect health information beyond what the user volunteers in chat.

**Right to access:**

- Users can request a copy of their data by contacting the studio.
- Admin dashboard provides lead and conversation data export.

**Right to deletion:**

- Users can request deletion by contacting the studio.
- Admin dashboard provides manual deletion of leads and conversations.
- Deletion cascades: deleting a lead removes linked conversation messages.

**Data retention:**

- Active leads: retained until closed.
- Closed leads: retained for 90 days, then available for deletion.
- Conversation data: retained for 180 days, then available for deletion.
- Analytics data: aggregated and anonymized; raw events deleted after 180 days.

### 10.4 Manual Deletion Support

Admin endpoints for data deletion:

- `DELETE /api/v1/admin/leads/{lead_id}` — owner role only.
- Deletes the lead and cascades to linked conversations and messages.
- Logs the deletion action with admin user ID and timestamp.

---

## 11. API Security Rules

### 11.1 Request Validation

- Validate all request bodies with Pydantic schemas.
- Reject malformed JSON with 422 status.
- Reject oversized requests with 413 status.
- Reject requests without required headers where applicable.
- Strip leading/trailing whitespace from string inputs.

### 11.2 Authentication Dependencies

- All admin routes use the `get_current_user` dependency.
- Role-based routes use the `require_role` dependency.
- Public routes (chat, leads) do not require authentication.
- Public routes are rate-limited to prevent abuse.

### 11.3 Role Checks

- Role checks happen at the dependency level, not in route handlers.
- Role is stored in the JWT payload and verified server-side.
- Role changes take effect on next token refresh.
- Never trust client-side role claims.

### 11.4 Request Size Limits

- Maximum request body: 100KB.
- Maximum chat message: 2000 characters.
- Maximum knowledge document content: 50,000 characters.
- Maximum lead notes: 2000 characters.
- Reject requests exceeding limits with 413 status.

### 11.5 Message Length Limits

- Chat message content: 2000 characters maximum.
- Messages exceeding this limit are rejected with a clear error message.
- The frontend enforces this limit client-side as well.

### 11.6 Public Endpoint Throttling

- Rate limiting applies to all public endpoints.
- Rate limits are per IP address.
- Rate limit headers are included in responses.
- Rate limit configuration is stored in application config, not hardcoded.

---

## 12. Production Security

### 12.1 Error Handling in Production

- Never expose stack traces in production error responses.
- Return generic error messages for 500 errors:

```json
{
  "detail": "An internal error occurred. Please try again later.",
  "status_code": 500
}
```

- Log full error details (including stack trace) internally.
- Use environment-aware error handlers (`ENVIRONMENT=production`).

### 12.2 Structured Logging

- All logs are structured JSON.
- Include request ID for distributed tracing.
- Include timestamp in ISO 8601 format.
- Include log level, service name, and endpoint.
- Exclude all sensitive data (see Section 7).

### 12.3 Security Headers

Add security headers to all responses:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 12.4 Health Check Endpoint

`GET /api/v1/health` returns:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

This endpoint does not reveal:
- Database connection details
- Internal service URLs
- API key status
- Stack traces

### 12.5 Deployment Security Checklist

Before every production deployment:

- [ ] All environment variables are set in the hosting platform.
- [ ] No secrets in source code or git history.
- [ ] CORS origins are set to production domains only.
- [ ] Rate limiting is active.
- [ ] `ENVIRONMENT` is set to `production`.
- [ ] Debug mode is disabled.
- [ ] Database migrations have been reviewed and applied.
- [ ] Admin user has a strong password.
- [ ] Health check endpoint responds correctly.
- [ ] No test data in production database.

### 12.6 Backup Strategy

- Railway PostgreSQL automated daily backups.
- Backup retention: 7 days.
- Test backup restoration monthly.
- Store backup credentials securely in the hosting platform.
- Never download backups to local machines with production data.
