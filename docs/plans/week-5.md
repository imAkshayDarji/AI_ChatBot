# Week 5 — Frontend Chat Widget and Admin Dashboard

> **Status:** COMPLETED
> **Depends on:** Week 4 completed
> **Blocks:** Week 6

---

## Contracts from Week 3 (frontend / API client)

- **Admin `POST …/admin/knowledge/{id}/reindex`** (wired in Week 3): MVP is **synchronous** — backend returns **`200 OK`** with a JSON body including **`chunk_count`** (not `202`). The web client must not assume async job polling.
- **Inspecting chunks** for debugging (**`GET …/chunks`**) is **out of MVP** — see **`TODOS.md`** ([P2] admin chunk inspection). Until then rely on DB or future endpoint.

---

## Alignment (CEO review, 2026-05-13)

- **Truthful dashboard:** Tasks 5.8 to 5.13 assume **authenticated admin HTTP APIs**, not mocks. **`apps/api/app/api/v1/router.py` today** exposes `health`, `admin/auth`, `admin/knowledge`, `chat/*`, **`POST`** `leads` only — no admin leads list, transcripts, aggregate analytics HTTP surface, or studio settings API. **`Task 5.0`** must land **before** those pages verify against “real data.”
- **Source of truth for shapes:** Freeze request/response fields against **`docs/API_CONTRACT.md`** and existing SQLAlchemy models; extend the contract doc when Week 5 adds routes.
- **Path prefix:** All browser and client calls use **`/api/v1/...`** (mounted in **`router.py`**). Short names like `/chat/start` in prose mean **`POST /api/v1/chat/start`**.
- **Streaming:** SSE is **`POST /api/v1/chat/message/stream`**. Clients must use **`fetch()` + `ReadableStream` + SSE line parsing**. **Do not use `EventSource`** for this endpoint (GET-only, … no POST body).
- **Package manager (`apps/web` has `bun.lock`):** Use **`cd apps/web && bun run build|lint|test`** for checks; `pnpm …` equivalents are fine if CI standardizes differently.

---

## Goal

Usable web MVP: customer-facing chat widget and admin dashboard. Both fully functional, mobile responsive, and connected to the backend (**real admin APIs**, see Task 5.0).

---

## Pre-Implementation Questions (ASK USER BEFORE STARTING)

1. What brand colors do you want for the chat widget? (Primary, secondary, accent)
2. Do you want the chat widget as a floating bubble (bottom-right) or embedded in a page?
3. What welcome message should the chat show? (Default: "Hey! Welcome to Krystal Tattoo Studio. How can I help you today?")
4. Should the admin dashboard require a separate login page, or share the main site layout?
5. Do you have a logo image file to use? (SVG or PNG)

---

## Tasks

### Task 5.0 — Admin backend REST (BLOCKING)

**What:** Implement the **missing** authenticated admin endpoints so Weeks 5.8 to 5.13 (and **`ApiClient` admin methods**) call real backends. Reuse **`Depends`** RBAC (`owner` / `admin` / `staff`) from **`apps/api/app/api/deps.py`**.

**Suggested modules (adjust names if you collapse routers):**

```
apps/api/app/api/v1/admin_leads.py
apps/api/app/api/v1/admin_conversations.py
apps/api/app/api/v1/admin_analytics.py
apps/api/app/api/v1/admin_settings.py   (optional single table + migration)
apps/api/app/api/v1/router.py           # include_* new routers
apps/api/app/tests/integration/*.py      # RBAC denial + happy path per area
```

**Route sketch (`/api/v1` prefix inherited from `router.py`):**

| Area | Verb + path | Notes |
|------|-------------|--------|
| Leads admin | **`GET`** `/admin/leads` | Pagination + filters (`status`, date range, `service_interest`); map to **`Lead`** model |
| Leads admin | **`GET`** `/admin/leads/{lead_id}` | Detail for expanded row |
| Leads admin | **`PATCH`** `/admin/leads/{lead_id}` | Status transitions per Week 5.9 (`new` … `closed`) |
| Chats admin | **`GET`** `/admin/conversations` | List (**session_id**/id, language, message count, started_at, linked lead); pagination |
| Chats admin | **`GET`** `/admin/conversations/{conversation_id}` | Full transcript incl. intents, sources, handoff/leads flags as stored (**read** persisted messages/metadata) |
| Analytics | **`GET`** `/admin/analytics/overview` | KPIs backing dashboard cards (conversation/lead counts, handoffs, failures, …) using **`analytics_events`** and/or existing tables |
| Analytics | **`GET`** `/admin/analytics/intents/popular` | Top intents (bounded) |
| Analytics | **`GET`** `/admin/analytics/queries/failed` | “Failed/low confidence” style rows from persisted signals (`rag_no_result`, etc.) — align names with DB |
| Studio settings | **`GET`** `/admin/settings/studio` | Values needed by Task 5.13 (phone, IG URL, welcome, quick replies, brand colors …) |
| Studio settings | **`PATCH`** `/admin/settings/studio` | If no row exists yet, add **Alembic migration** (e.g. `studio_settings` single-row or keyed JSON) … **cannot** ship a write-only UI with nothing to PATCH |

**Constraints:**

- Pagination and filter params consistent with **`GET /admin/knowledge`** patterns.
- **No N+1** on list endpoints (use **`selectinload`/`joinedload`** or aggregate SQL as appropriate).
- **DELETE** leads/conversations: **optional in Week 5**; **`docs/plans/week-6.md`** Task 6.5 assumes admin delete capability — implement delete here if timeboxed or defer explicitly to Week 6.

**Verification:**

- **`pytest`** integration: unauthenticated **`401`**, authenticated **`200`** slices per router.
- **Manual:** each new path returns JSON that matches **`docs/API_CONTRACT.md`** updates you add for Week 5.

---

### Task 5.1 — API Client Library

**What:** **Extend** the centralized API client (**`apps/web/lib/api.ts`** already exposes minimalist **`apiGet` / `apiPost`** helpers; **`types/api.ts`** currently **`HealthResponse` only**) for all frontend-to-backend traffic.

**Files:**

```
apps/web/lib/api.ts           # extend (do not orphan existing helpers unless replacing deliberately)
apps/web/lib/auth.ts          # create
apps/web/lib/constants.ts     # create
apps/web/types/api.ts        # extend
```

**Imports:** Prefer **`@/…`** aliases per project **`PLAN.md`** / ESLint conventions.

**api.ts:**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  status: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  // Chat endpoints
  async startChat(language: string, channel: string = "web"): Promise<ChatStartResponse> { ... }
  async sendMessage(sessionId: string, message: string, language: string): Promise<ChatMessageResponse> { ... }
  async streamMessage(sessionId: string, message: string, language: string): AsyncGenerator<StreamChunk> { ... }
  async submitFeedback(messageId: string, rating: number, comment?: string): Promise<void> { ... }

  // Lead endpoints
  async submitLead(data: LeadCreateRequest): Promise<LeadResponse> { ... }

  // Admin endpoints (with auth) — backend returns access + refresh (Week 2)
  async adminLogin(email: string, password: string): Promise<TokenResponse> { ... }
  async adminRefresh(refreshToken: string): Promise<TokenResponse> { ... }
  async getMe(): Promise<UserResponse> { ... }

  // Admin knowledge
  async listKnowledge(params?: ListParams): Promise<PaginatedResponse<KnowledgeDocument>> { ... }
  async createKnowledge(data: KnowledgeCreateRequest): Promise<KnowledgeDocument> { ... }
  async updateKnowledge(id: string, data: Partial<KnowledgeCreateRequest>): Promise<KnowledgeDocument> { ... }
  async deleteKnowledge(id: string): Promise<void> { ... }
  async reindexKnowledge(id: string): Promise<{ message: string; document_id: string; chunk_count: number }> { ... }

  // Admin leads
  async listLeads(params?: ListParams): Promise<PaginatedResponse<LeadResponse>> { ... }
  async getLead(id: string): Promise<LeadResponse> { ... }
  async updateLead(id: string, data: Partial<LeadUpdateRequest>): Promise<LeadResponse> { ... }

  // Admin chats
  async listChats(params?: ListParams): Promise<PaginatedResponse<ConversationResponse>> { ... }
  async getChat(id: string): Promise<ConversationDetailResponse> { ... }

  // Admin analytics
  async getAnalyticsOverview(): Promise<AnalyticsOverview> { ... }
  async getPopularIntents(): Promise<IntentStats[]> { ... }
  async getFailedQueries(): Promise<FailedQuery[]> { ... }

  // Admin settings
  async getSettings(): Promise<StudioSettings> { ... }
  async updateSettings(data: Partial<StudioSettings>): Promise<StudioSettings> { ... }
}

export const api = new ApiClient(API_URL);
```

**auth.ts:**

```typescript
// Access + refresh token storage (Week 2: POST /admin/auth/login and /admin/auth/refresh)
export function getAccessToken(): string | null { ... }
export function setAccessToken(token: string): void { ... }
export function getRefreshToken(): string | null { ... }
export function setRefreshToken(token: string): void { ... }
export function removeTokens(): void { ... }
export function isAuthenticated(): boolean { ... }
// On 401 from an admin call: try adminRefresh once with stored refresh, then redirect to login if it fails
```

**types/api.ts:**

```typescript
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ChatStartResponse { 
  session_id: string; 
  message: string; 
  quick_replies: string[]; 
}
export interface ChatMessageResponse { 
  message_id: string; 
  conversation_id: string; 
  content: string; 
  intent: string | null; 
  sources: SourceReference[]; 
  handoff: HandoffInfo | null; 
  lead_capture_suggested: boolean; 
  suggested_replies: string[]; 
}
export interface StreamChunk {
  event: "chunk" | "done" | "error";
  data: {
    content?: string;
    message_id?: string;
    conversation_id?: string;
    sources?: SourceReference[];
    suggested_replies?: string[];
    error?: string;
  };
}
export interface LeadCreateRequest { ... }
export interface LeadResponse { ... }
export interface KnowledgeDocument { ... }
export interface ConversationResponse { ... }
export interface AnalyticsOverview { ... }
// ... all API response types
```

**Constraints:**
- All API calls go through this single client (**class + helpers** acceptable; avoid duplicating two competing clients)
- **`NEXT_PUBLIC_API_URL`** is the origin only (**no trailing `/api/v1`**); each method prefixes paths with **`/api/v1`** where applicable
- Handle 401 on admin routes → attempt refresh (**`POST /api/v1/admin/auth/refresh`**), then redirect to login if refresh fails
- Handle network errors gracefully
- TypeScript strict types for all responses
- **`streamMessage`:** **`fetch()` POST** to **`/api/v1/chat/message/stream`**, consume **`ReadableStream`**, incrementally parse **`data:`** SSE chunks (buffer partial lines across reads). Use **`AbortController`** for cancel/unmount. **Do not use `EventSource`.** Vitest-covered parser helper strongly recommended.
- Handle rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`) from responses

**JWT in `localStorage`:** Acceptable MVP; pair with CSP/dependency hygiene. **HTTP-only cookie auth** stays future hardening (**`TODOS.md` / Week 6** narrative).

**Verification:**
- TypeScript compiles without errors
- All types match backend API schemas

---

### Task 5.2 — Chat Widget Component

**What:** Build the main chat widget UI.

**Files to create:**

```
apps/web/components/chat/ChatWidget.tsx
apps/web/components/chat/MessageBubble.tsx
apps/web/components/chat/QuickReplies.tsx
apps/web/components/chat/InputBar.tsx
```

**ChatWidget.tsx:**

State management:
```typescript
interface ChatState {
  sessionId: string | null;
  messages: Message[];
  isLoading: boolean;
  language: string;
  error: string | null;
}
```

Features:
- Floating bubble button (bottom-right corner)
- Expandable chat panel (350px wide, 500px tall on desktop, full-width on mobile)
- Welcome message on open
- Message list with auto-scroll to bottom
- Input bar with send button
- Quick reply buttons (static from /chat/start AND dynamic suggested_replies from AI response)
- Streaming response display (tokens appear word-by-word via SSE)
- Loading indicator during AI response
- Language selector in header
- Close/minimize button

**MessageBubble.tsx:**

Props:
```typescript
interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: SourceReference[];
  handoff?: HandoffInfo;
}
```

Features:
- User messages right-aligned, primary color background
- Assistant messages left-aligned, light background
- Source references shown as collapsible "Sources" link
- Handoff card shown inline when applicable (with phone/Instagram links)
- Markdown rendering for assistant messages (**`react-markdown`** or equivalent with **tight allow-list**; Week 4 already sanitizes on server … do not **`dangerouslySetInnerHTML`** with raw model output)

**Streaming / UX edge cases:**

- **`AbortController`:** abort in-flight **`streamMessage`** on panel close/navigate-away
- **Double-send:** disable send while a turn is streaming or debounce (**idempotent**/single-flight UX)
- Timestamp shown below each message

**QuickReplies.tsx:**

Props:
```typescript
interface QuickRepliesProps {
  replies: string[];
  onSelect: (reply: string) => void;
}
```

Features:
- Horizontal scrollable pill buttons
- Static options from `/chat/start` response
- Dynamic suggestions from `suggested_replies` in each AI response (replaces static options when present)
- Selecting a quick reply sends it as a message

**InputBar.tsx:**

Features:
- Text input with max 1000 chars
- Send button (disabled when empty or loading)
- Enter key to send
- Disabled state during loading

**Constraints:**
- Use Tailwind CSS only (no inline styles)
- Mobile responsive (full width on small screens)
- Accessible (ARIA labels, keyboard navigation)
- Use `'use client'` directive only on components that need it
- ChatWidget wrapper is client component, MessageBubble can be server-compatible

**Verification:**
- Chat bubble renders on page
- Clicking opens chat panel
- Can type and send messages
- Messages display correctly
- Quick replies work
- Works on mobile viewport

---

### Task 5.3 — Language Selector Component

**What:** Language switcher for multilingual support.

**Files to create:**

```
apps/web/components/chat/LanguageSelector.tsx
```

**Features:**
- Dropdown with 3 options: English, Hindi, Gujarati
- Shows current language with flag/label
- Changing language sends new `chat/start` with selected language
- Persists selection in localStorage

**Verification:**
- Language selector renders in chat header
- Selecting Hindi restarts chat in Hindi
- Selecting Gujarati restarts chat in Gujarati

---

### Task 5.4 — Lead Capture Form Component

**What:** Inline form for capturing lead details.

**Files to create:**

```
apps/web/components/chat/LeadCaptureForm.tsx
```

**Features:**
- Triggered by "lead_capture_suggested" flag in AI response
- Fields: name, email, phone, service_interest (optional), **`preferred_language`** aligned with **`ChatWidget`** (**`en`/`hi`/`gu`** per backend **`LeadCreateRequest`**)
- Consent checkbox: "By submitting your details, you agree that the studio can contact you about your enquiry."
- **JSON body MUST include **`consent: true`** (literal **`true`** per backend **`LeadCreateRequest`** … unchecked submit is invalid)**
- Client-side validation (email format, required fields)
- Submit to **`POST /api/v1/leads`** with **`Content-Type: application/json`**
- Success/error feedback
- Form resets after submission

**Constraints:**
- Must show consent text
- Must require consent checkbox to be checked
- Validate email format on client side
- Do not store sensitive data locally

**Verification:**
- Form appears when suggested by AI
- Submit creates lead via API
- Validation works (empty fields, bad email)
- Consent checkbox required

---

### Task 5.5 — Handoff Card Component

**What:** Display handoff information when AI suggests contacting studio.

**Files to create:**

```
apps/web/components/chat/HandoffCard.tsx
```

**Features:**
- Shows when `handoff.should_handoff` is true
- Displays handoff message
- Clickable phone number (tel: link)
- Clickable Instagram link (opens in new tab)
- Styled as a distinct card within chat

**Verification:**
- Handoff card appears for medical/unanswerable queries
- Phone link opens dialer on mobile
- Instagram link opens in new tab

---

### Task 5.6 — Integrate Chat Widget on Main Page

**What:** Add the chat widget to the main landing page.

**Files to modify:**

```
apps/web/app/page.tsx
apps/web/app/layout.tsx
```

**page.tsx:**

```tsx
export default function HomePage() {
  return (
    <main>
      <h1>Krystal Tattoo Studio</h1>
      <p>Tattoo, Piercing, and Dreadlock Studio</p>
      {/* Chat widget rendered here or in layout */}
      <ChatWidget />
    </main>
  );
}
```

**layout.tsx:**

- Set metadata (title, description)
- Load fonts (Inter or system fonts)
- Set up global styles

**Verification:**
- Main page loads with studio name
- Chat widget appears as floating bubble
- Full chat flow works end-to-end from browser

---

### Task 5.7 — Admin Login Page

**What:** Create the admin login page.

**Files to create:**

```
apps/web/app/admin/login/page.tsx
apps/web/app/admin/layout.tsx
apps/web/components/admin/AdminLayout.tsx
```

**Features:**
- Email and password form
- Submit to **`POST /api/v1/admin/auth/login`**
- Store JWT in localStorage
- Redirect to `/admin/dashboard` on success
- Show error message on failure
- Redirect to `/admin/dashboard` if already logged in

**AdminLayout.tsx:**
- Check authentication on mount
- Redirect to login if no valid token
- Render sidebar navigation + main content area
- Sidebar links: Dashboard, Leads, Chats, Knowledge, Analytics, Settings, Logout

**Verification:**
- `/admin/login` renders login form
- Login with correct credentials redirects to dashboard
- Login with wrong credentials shows error
- Accessing `/admin/dashboard` without token redirects to login

---

### Task 5.8 — Admin Dashboard Overview

**What:** Create the main admin dashboard page.

**Files to create:**

```
apps/web/app/admin/dashboard/page.tsx
apps/web/components/admin/AnalyticsCards.tsx
```

**Dashboard shows:**
- Total conversations (today, this week, all time)
- Total leads (today, this week, all time)
- Lead conversion rate
- Active knowledge documents
- Recent handoffs
- Popular intents (top 5)
- Recent failed queries

**AnalyticsCards.tsx:**
- Grid of stat cards
- Each card: title, value, trend indicator (up/down)

**Verification:**

- **Depends on Task 5.0** analytics/overview routes
- Dashboard loads with real data from API
- Stat cards show correct numbers
- Protected by auth

---

### Task 5.9 — Admin Leads Page

**What:** Create the leads management page.

**Files to create:**

```
apps/web/app/admin/leads/page.tsx
apps/web/components/admin/LeadTable.tsx
```

**Features:**
- Table with columns: Name, Email, Phone, Service, Status, Date
- Status badge (color-coded: new=green, contacted=blue, converted=gold, closed=gray)
- Click row to expand details (notes, placement, style, budget, linked conversation)
- Status dropdown to update (new -> contacted -> consultation_booked -> converted -> closed)
- Filters: status, date range, service interest
- Pagination (20 per page)
- Export to CSV button (future, just placeholder for MVP)

**Verification:**

- **Depends on Task 5.0** leads admin routes

- Leads table renders with data
- Can update lead status
- Can filter by status
- Pagination works

---

### Task 5.10 — Admin Chat History Page

**What:** Create the chat history viewer.

**Files to create:**

```
apps/web/app/admin/chats/page.tsx
apps/web/components/admin/ChatTranscript.tsx
```

**Features:**
- List of conversations with: session_id, language, message count, date, lead linked
- Click to view full transcript
- Transcript shows all messages in chronological order
- Show intent and confidence for each message
- Show sources used for each assistant message
- Show handoff events
- Show lead capture events
- Filter by language, date range
- Pagination

**Verification:**

- **Depends on Task 5.0** conversations routes

- Chat list loads
- Clicking a conversation shows full transcript
- Messages render with metadata

---

### Task 5.11 — Admin Knowledge Editor Page

**What:** Create the knowledge management page.

**Files to create:**

```
apps/web/app/admin/knowledge/page.tsx
apps/web/components/admin/KnowledgeEditor.tsx
```

**Features:**
- List of knowledge documents with: title, source_type, status, language, date
- "Add Document" button opens form
- Edit document: title, content (textarea/richtext), source_type, language, service_type, status
- Delete document with confirmation dialog
- "Reindex" button per document
- Status toggle (draft/active/archived)
- Search/filter by title, service_type, status
- Show chunk count per document

**KnowledgeEditor.tsx:**
- Rich text area for content editing
- Character count
- Preview of content
- Save and Reindex buttons

**Verification:**
- Knowledge list loads
- Can create new document
- Can edit existing document
- Can delete with confirmation
- Reindex calls succeed (**HTTP 200**); show confirmation using **`chunk_count`** when the API returns it
- Status changes persist

---

### Task 5.12 — Admin Analytics Page

**What:** Create the analytics dashboard.

**Files to create:**

```
apps/web/app/admin/analytics/page.tsx
```

**Features:**
- Popular intents chart (bar chart or table)
- Failed queries table (query, date, count)
- Handoff rate
- Lead conversion funnel
- Language distribution
- Message volume over time (last 7 days)
- Average AI confidence score

**Note:** Use simple tables/cards for MVP. Charts can use a lightweight library or just CSS bars.

**Verification:**

- **Depends on Task 5.0** analytics routes

- Analytics page loads with real data
- All metrics render correctly

---

### Task 5.13 — Admin Settings Page

**What:** Create the studio settings page.

**Files to create:**

```
apps/web/app/admin/settings/page.tsx
```

**Features:**
- Studio name (read from config)
- Studio phone
- Studio Instagram URL
- Studio opening hours
- Welcome message for chatbot
- Quick replies configuration
- Brand color picker (for chat widget)

**Note:** For MVP, settings are read-only or minimal. Full settings management is Phase 2.

**Verification:**

- **Depends on Task 5.0** settings routes (+ migration when writes enabled)

- Settings page loads
- Current settings display correctly

---

## Testing Checklist (Run After ALL Tasks Complete)

### Frontend Tests

From **`apps/web`** (canonical: **`bun.lock`**):

- [ ] TypeScript build: `bun run build` (or `pnpm build` if CI uses **pnpm`)
- [ ] Lint: `bun run lint`
- [ ] Unit tests: `bun run test`
- [ ] Chat widget renders on main page
- [ ] Chat bubble opens chat panel
- [ ] Can send a message and receive AI response
- [ ] Streaming responses display word-by-word
- [ ] Static quick replies work (from **`POST /api/v1/chat/start`**)
- [ ] Dynamic suggested replies replace static options after AI response
- [ ] Language selector switches languages
- [ ] Lead capture form validates and submits
- [ ] Handoff card shows with contact info
- [ ] Mobile responsive (< 375px viewport)
- [ ] Admin login page works
- [ ] Admin dashboard shows stats
- [ ] Admin leads page shows leads table
- [ ] Admin can update lead status
- [ ] Admin chat history shows transcripts
- [ ] Admin knowledge editor can CRUD documents
- [ ] Admin knowledge reindex works (expects **HTTP 200** + `chunk_count` from backend)
- [ ] Admin analytics page shows metrics
- [ ] Admin settings page shows current settings
- [ ] All admin pages require authentication
- [ ] Unauthorized users redirected to login
- [ ] Channel **`"web"`** passed to **`POST /api/v1/chat/start`**
- [ ] **Task 5.0** merged: admin API integration tests green in CI (**`pytest`**)

### Manual Cross-Browser Test
- [ ] Chrome (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

---

## Git Commit Strategy

Stage **intentionally** (**avoid `git add -A`** in shared branches … reduces accidental secret or noise commits):

```bash
# After Task 5.0
git add apps/api/app/api/v1/admin_*.py apps/api/app/api/v1/router.py apps/api/alembic/versions/*_studio*.py apps/api/app/tests/integration/…
git commit -m "feat(api): add admin leads, conversations, analytics, settings routes"

# After Task 5.1
git add apps/web/lib/api.ts apps/web/lib/auth.ts apps/web/types/api.ts …
git commit -m "feat(web): extend API client, auth helpers, and types"

# After Task 5.2-5.5
git add apps/web/components/chat …
git commit -m "feat(web): add chat widget, language selector, lead form, handoff card"

# After Task 5.6
git add apps/web/app/page.tsx apps/web/app/layout.tsx …
git commit -m "feat(web): integrate chat widget on landing page"

# After Task 5.7-5.8
git add apps/web/app/admin apps/web/components/admin …
git commit -m "feat(web): add admin login, layout, dashboard overview"

# After Task 5.9-5.10
git add apps/web/app/admin/leads … apps/web/app/admin/chats …
git commit -m "feat(web): admin leads and chat history"

# After Task 5.11-5.13
git add apps/web/app/admin/knowledge … apps/web/app/admin/analytics … apps/web/app/admin/settings …
git commit -m "feat(web): admin knowledge, analytics, settings"

# Push when ready (use your branch workflow)
git push origin <branch>
```

---

## After Week 5 Completion

- [ ] Update **`docs/API_CONTRACT.md`** … all **Task 5.0** routes + types the web client uses
- [ ] Update PLAN.md checklist — mark Phase 13, 14 items as done
- [ ] Update this file's status to COMPLETED
- [ ] Proceed to `docs/plans/week-6.md`
