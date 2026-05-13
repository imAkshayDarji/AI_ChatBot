# Product Specification — Krystal Studio AI Chatbot

> **Source of truth:** This document defines the product scope, user personas, user stories, and success criteria for the Krystal Studio AI Chatbot MVP. Read PLAN.md before modifying this file.

---

## 1. Product Overview

**Product:** Production-grade AI chatbot platform for **Krystal Tattoo Studio**, a Tattoo, Piercing, and Dreadlock Studio.

**Studio Location:** 2nd floor, Signature Arcade, 203, Gangotri Cir Rd, Nikol, Ahmedabad, Gujarat 382350, India

**Studio Hours:**
- Monday–Saturday: 11:30 am – 10:00 pm
- Sunday: 12:00 pm – 10:00 pm

**Studio Phone:** +91-XXXX-XXXXXX

**Studio Instagram:** https://www.instagram.com/krystaltattoostudio

The chatbot is embedded on the studio's website as a chat widget. It answers customer questions, explains services, provides pricing guidance, captures leads, and hands off to human staff when needed — all in multiple languages.

---

## 2. Main Goals

| # | Goal | Description |
|---|------|-------------|
| G1 | Answer customer questions | Respond accurately to queries about services, policies, aftercare, and the studio |
| G2 | Explain services | Describe tattoo, piercing, and dreadlock services clearly |
| G3 | Provide pricing guidance | Give price ranges and factors that affect pricing without inventing exact quotes |
| G4 | Provide aftercare guidance | Share aftercare instructions for tattoos, piercings, and dreadlocks |
| G5 | Recommend options | Suggest tattoo styles, piercing types, and dreadlock services based on customer preferences |
| G6 | Capture customer leads | Collect name, email, phone, and service interest from potential customers |
| G7 | Support multilingual conversations | Allow conversations in English, Hindi, and Gujarati |
| G8 | Reduce manual support work | Handle repetitive questions automatically so staff can focus on in-studio customers |
| G9 | Prepare for future expansion | Architecture supports future booking, WhatsApp, Instagram, CRM, and AI receptionist features |

---

## 3. Supported Languages

| Language | Code | Priority |
|----------|------|----------|
| English | `en` | Default. All knowledge must be available in English |
| Hindi | `hi` | Full support |
| Gujarati | `gu` | Full support |

Language selection happens in the chat widget. The system prefers knowledge in the selected language and falls back to English when needed.

---

## 4. Brand Tone

The chatbot embodies the studio's personality:

- **Professional** — Knowledgeable about tattoo, piercing, and dreadlock topics
- **Friendly** — Warm and approachable, not robotic
- **Casual studio vibe** — Conversational, like talking to someone at the studio
- **Trustworthy** — Accurate, never fabricates information
- **Helpful** — Goes beyond the minimum to guide customers
- **Honest when unsure** — Says "I'm not sure about that" and offers handoff instead of guessing

---

## 5. Target Traffic

- **Initial traffic:** Less than 100 users/day
- **Architecture:** Must support future scaling without re-architecture
- **Cost target:** Minimal infrastructure cost at low traffic (Railway hobby plan + Vercel free tier)

---

## 6. MVP Scope

### 6.1 Included in MVP

| Feature | Description |
|---------|-------------|
| Public chat widget | Embedded chat on the studio website |
| Language selection | User can choose English, Hindi, or Gujarati |
| RAG FAQ answering | Answers based on studio knowledge base using retrieval-augmented generation |
| Service information | Details about tattoo, piercing, and dreadlock services |
| Pricing guidance | Price ranges and pricing factors (not exact quotes) |
| Aftercare guidance | Post-service care instructions |
| Lead capture | Collect customer contact details and service interest |
| Human handoff | Route complex questions to studio phone or Instagram |
| Admin login | JWT-based authentication for studio staff |
| Knowledge management | Admin CRUD for knowledge documents |
| Lead dashboard | Admin view of captured leads with status management |
| Chat history | Admin view of conversation transcripts |
| Basic analytics | Popular intents, failed queries, lead conversion metrics |
| Deployment | Railway (backend + database) + Vercel (frontend) |
| Rate limiting | Protect public endpoints from abuse |
| Basic security | Input validation, CORS, no secrets in frontend, PII-safe logging |

### 6.2 Excluded from MVP

These features are explicitly **not** in MVP. Architecture should support them later.

- Appointment booking / calendar sync
- WhatsApp integration
- Instagram DM automation
- CRM automation
- Image analysis (tattoo design upload/analysis)
- Voice calls / AI receptionist phone system
- Payments
- Multi-studio support
- Advanced long-term memory
- Streaming chat responses
- Redis caching
- Background workers
- Email notifications

---

## 7. User Personas

### Persona 1: Website Visitor

**Who:** A potential customer visiting the Krystal Tattoo Studio website.

**Demographics:** Ages 18–45, located in or around Ahmedabad, Gujarat, India. May speak English, Hindi, or Gujarati.

**Goals:**
- Learn about available services (tattoo, piercing, dreadlock)
- Get a sense of pricing
- Understand aftercare requirements
- Decide whether to visit the studio
- Contact the studio or leave their details

**Pain points:**
- Doesn't want to call during business hours
- Unsure about pricing — hesitant to ask in person
- Wants quick answers about aftercare
- May prefer Hindi or Gujarati over English
- Wants to feel confident before visiting

**Technical comfort:** Moderate. Using a phone or laptop browser. Expects a simple chat interface.

---

### Persona 2: Studio Admin / Owner

**Who:** The studio owner or staff member managing the chatbot and leads.

**Goals:**
- Keep knowledge base accurate and up-to-date
- Review and follow up on captured leads
- Monitor chat quality and failed queries
- Understand what customers are asking about
- Update pricing, services, and aftercare info

**Pain points:**
- Manually answering the same questions repeatedly
- Losing track of potential customers
- Not knowing what questions the chatbot fails to answer
- Needs a simple admin interface, not a complex system

**Technical comfort:** Low to moderate. Comfortable with web dashboards. Not a developer.

---

## 8. User Stories

### 8.1 Website Visitor Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| V-01 | As a visitor, I want to open the chat widget and see a welcome message so I know what the chatbot can help with | Chat widget opens with a branded welcome message explaining available topics |
| V-02 | As a visitor, I want to select my preferred language so I can chat comfortably | Language selector offers English, Hindi, Gujarati; chat responds in selected language |
| V-03 | As a visitor, I want to ask about tattoo services and get accurate information | Chatbot returns service details from the knowledge base |
| V-04 | As a visitor, I want to ask about piercing services and get accurate information | Chatbot returns piercing service details from the knowledge base |
| V-05 | As a visitor, I want to ask about dreadlock services and get accurate information | Chatbot returns dreadlock service details from the knowledge base |
| V-06 | As a visitor, I want to ask about pricing and get a helpful range | Chatbot provides price ranges with factors (size, placement, complexity) and advises visiting for exact quotes |
| V-07 | As a visitor, I want to ask about aftercare and get proper instructions | Chatbot returns aftercare guidance from the knowledge base |
| V-08 | As a visitor, I want to share my contact details so the studio can follow up | Lead capture form appears; details are saved and visible to admin |
| V-09 | As a visitor, I want the chatbot to tell me when it cannot answer and offer to connect me to the studio | Handoff message appears with studio phone and Instagram link |
| V-10 | As a visitor, I want the chatbot to remember my conversation context so I don't repeat myself | Conversation history is maintained within the session |
| V-11 | As a visitor, I want to rate the chatbot's answer so the studio can improve | Thumbs up/down feedback on each response |
| V-12 | As a visitor, I want to ask in Hindi or Gujarati and be understood | Language detection and response in the selected language works |
| V-13 | As a visitor, I want the chat to work on my phone | Chat widget is fully responsive on mobile browsers |

### 8.2 Studio Admin / Owner Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| A-01 | As an admin, I want to log in securely so I can access the admin dashboard | JWT-based login with role-based access |
| A-02 | As an admin, I want to view all captured leads in a table so I can follow up | Lead table shows name, contact, service interest, status, date |
| A-03 | As an admin, I want to update lead status so I can track progress | Lead status can be changed (new → contacted → consultation_booked → converted → closed) |
| A-04 | As an admin, I want to view chat transcripts so I can review quality | Conversation list with full message history viewable |
| A-05 | As an admin, I want to add and edit knowledge documents so the chatbot stays accurate | Knowledge CRUD with title, content, language, service type |
| A-06 | As an admin, I want to reindex knowledge after editing so changes take effect immediately | Reindex endpoint regenerates chunks and embeddings |
| A-07 | As an admin, I want to see which questions are asked most often so I can improve knowledge | Popular intents analytics view |
| A-08 | As an admin, I want to see which questions the chatbot failed to answer so I can add knowledge | Failed queries analytics view |
| A-09 | As an admin, I want to see basic analytics on the dashboard | Overview shows total chats, total leads, conversion rate, popular services, languages |
| A-10 | As an admin, I want to update studio settings so the chatbot reflects current information | Settings page for configurable chatbot parameters |

---

## 9. Success Criteria

The MVP is successful when:

| # | Criterion | Measurement |
|---|-----------|-------------|
| S1 | Customers get useful answers | ≥70% of chat sessions end without handoff |
| S2 | Studio receives real enquiries | ≥5 leads captured per week after launch |
| S3 | Staff can update knowledge | Admin can create/edit/delete knowledge documents without developer help |
| S4 | AI failures are visible | Failed queries appear in admin analytics within 24 hours |
| S5 | System runs safely in production | No data leaks, no exposed secrets, no unauthorized admin access |
| S6 | Multilingual support works | Hindi and Gujarati conversations return accurate responses |
| S7 | Mobile experience is good | Chat widget is fully usable on mobile browsers |
| S8 | Response quality is acceptable | ≥60% positive feedback rating on chatbot responses |

---

## 10. Handoff Strategy

### 10.1 When to Hand Off

The chatbot triggers a handoff when:

- Low confidence in the answer (below threshold)
- No relevant knowledge found in RAG retrieval
- Medical or infection concern mentioned
- Exact price requested (requires in-person consultation)
- Booking or appointment confirmation requested
- Legal or age restriction edge case
- User is angry or frustrated
- Complex custom design discussion
- Studio policy is unclear

### 10.2 Handoff Message

The handoff message directs the visitor to real human contact:

> "I don't want to guess on that. Best option is to contact the studio directly — call **+91-XXXX-XXXXXX** or message the official Instagram **[@krystaltattoostudio](https://www.instagram.com/krystaltattoostudio)** so the team can confirm it properly."

### 10.3 Handoff Contact Channels

| Channel | Value |
|---------|-------|
| Phone | +91-XXXX-XXXXXX |
| Instagram | https://www.instagram.com/krystaltattoostudio |

### 10.4 Handoff Flow

```
Chatbot detects handoff trigger
     ↓
Sends handoff message with contact details
     ↓
Logs handoff event in analytics (handoff_triggered + reason)
     ↓
Offers lead capture form (if not already captured)
     ↓
Visitor can continue chatting or leave
```

---

## 11. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Chat response < 5 seconds for 95th percentile |
| Availability | 99% uptime target during studio hours |
| Security | All admin endpoints authenticated; no secrets in frontend; rate limiting on public endpoints |
| Privacy | Only collect necessary PII; consent text on lead capture; manual data deletion supported |
| Scalability | Architecture supports 100+ concurrent users without rework |
| Accessibility | Chat widget works on Chrome, Safari, Firefox, mobile browsers |
| Cost | Under ₹3,000/month infrastructure at < 100 users/day |
| Logging | Structured logs; no PII in logs; request tracking with correlation IDs |

---

## 12. Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+ / TypeScript / Tailwind CSS / shadcn/ui |
| Backend | Python 3.12 / FastAPI / SQLAlchemy (async) / Alembic |
| Database | PostgreSQL 16 + pgvector |
| AI | OpenAI GPT-4o-mini (chat) / OpenAI text-embedding-3-large (embeddings) |
| Hosting (Backend) | Railway |
| Hosting (Frontend) | Vercel |
| Development | Cursor IDE + GLM-5.1 |
