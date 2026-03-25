# AI Tutor Platform — Dependencies, Limitations & Solutions

## Table of Contents

- [System Requirements](#system-requirements)
- [Dependencies](#dependencies)
- [External Services & API Keys](#external-services--api-keys)
- [Features Currently Implemented](#features-currently-implemented)
- [Features NOT Yet Implemented (Backend)](#features-not-yet-implemented-backend)
- [Frontend Dependencies — Features Waiting on Frontend](#frontend-dependencies--features-waiting-on-frontend)
- [Limitations & Constraints](#limitations--constraints)
- [Solutions, Approaches & Cost Estimates](#solutions-approaches--cost-estimates)
- [Animation & Visual Stimulation — The Main Challenge](#animation--visual-stimulation--the-main-challenge)
- [Infrastructure Recommendations](#infrastructure-recommendations)

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10+ | 3.11+ |
| PostgreSQL | 14+ | 16+ |
| Redis | 6.0+ | 7.0+ |
| RAM | 2 GB | 4 GB+ |
| Disk | 1 GB + uploads | 10 GB+ |
| OS | Linux / macOS / Windows | Ubuntu 22.04 LTS |

---

## Dependencies

### Core Framework
| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.115.6 | Async web framework — REST + WebSocket |
| uvicorn[standard] | 0.34.0 | ASGI server with hot-reload |
| python-multipart | 0.0.18 | Form / file upload parsing |
| websockets | 14.1 | WebSocket protocol support |

### Database & ORM
| Package | Version | Purpose |
|---|---|---|
| sqlalchemy[asyncio] | 2.0.36 | Async ORM with relationship mapping |
| asyncpg | 0.30.0 | PostgreSQL async driver |
| alembic | 1.14.0 | Database migrations |
| psycopg2-binary | 2.9.10 | Sync PG driver (for Alembic offline mode) |

### Caching
| Package | Version | Purpose |
|---|---|---|
| redis | 5.2.1 | Redis client — session cache, segment caching |
| aioredis | 2.0.1 | Async Redis operations |

### Authentication & Security
| Package | Version | Purpose |
|---|---|---|
| python-jose[cryptography] | 3.3.0 | JWT token creation and verification |
| passlib[bcrypt] | 1.7.4 | Password hashing (bcrypt) |
| bcrypt | 4.2.1 | Bcrypt backend |
| email-validator | 2.2.0 | Email format validation |

### Validation
| Package | Version | Purpose |
|---|---|---|
| pydantic | 2.10.3 | Request/response data validation |
| pydantic-settings | 2.7.0 | Settings from environment variables |

### AI Integration
| Package | Version | Purpose |
|---|---|---|
| openai | 1.58.1 | OpenAI API (unused — we use raw httpx) |
| httpx | 0.28.1 | Async HTTP client for OpenAI & ElevenLabs |

### Media Processing
| Package | Version | Purpose |
|---|---|---|
| pytesseract | 0.3.13 | OCR for doubt image uploads |
| Pillow | 11.0.0 | Image processing for OCR |
| reportlab | 4.2.5 | PDF notes generation |

### Document Processing
| Package | Version | Purpose |
|---|---|---|
| PyMuPDF | 1.24.14 | PDF text extraction (fitz) |
| python-docx | 1.1.2 | DOCX/Word document text extraction |

### File Handling
| Package | Version | Purpose |
|---|---|---|
| python-magic | 0.4.27 | File MIME type detection |
| aiofiles | 24.1.0 | Async file I/O |

### 2FA / TOTP
| Package | Version | Purpose |
|---|---|---|
| pyotp | 2.9.0 | TOTP generation and verification |
| qrcode[pil] | 8.0 | QR code generation for authenticator setup |

### Rate Limiting
| Package | Version | Purpose |
|---|---|---|
| slowapi | 0.1.9 | Per-user rate limiting middleware |

### Utilities
| Package | Version | Purpose |
|---|---|---|
| python-dotenv | 1.0.1 | Load .env files |
| uuid6 | 2024.7.10 | UUID generation utilities |

### Testing
| Package | Version | Purpose |
|---|---|---|
| pytest | 8.3.4 | Test runner |
| pytest-asyncio | 0.25.0 | Async test support |
| pytest-cov | 6.0.0 | Code coverage |

### System Dependencies (non-Python)
| Dependency | Purpose | Install |
|---|---|---|
| Tesseract OCR | Required by pytesseract for image-to-text | `apt install tesseract-ocr` / `brew install tesseract` |
| libmagic | Required by python-magic for file type detection | `apt install libmagic1` / `brew install libmagic` |
| PostgreSQL | Primary database | `apt install postgresql` |
| Redis | Caching layer | `apt install redis-server` |

---

## External Services & API Keys

| Service | Purpose | Required | Free Tier |
|---|---|---|---|
| **OpenAI API** | LLM for content generation, doubt resolution, MCQ generation, chat | Yes | No — Pay-per-token |
| **ElevenLabs API** | Text-to-Speech synthesis with voice personality | Yes (for TTS) | 10,000 chars/month free |
| **Email Service** | OTP verification, password reset | No (disabled by default) | Depends on provider |

### OpenAI Cost Estimates
| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical Session Cost |
|---|---|---|---|
| gpt-4o | $2.50 | $10.00 | $0.03–$0.08 per session |
| gpt-4o-mini | $0.15 | $0.60 | $0.002–$0.005 per session |

A typical 30-minute session generates ~5,000–15,000 tokens (system prompt + segments + interactions).

### ElevenLabs Cost Estimates
| Plan | Characters/month | Cost | Estimated Sessions |
|---|---|---|---|
| Free | 10,000 | $0 | ~2–3 sessions |
| Starter | 30,000 | $5/month | ~8–10 sessions |
| Creator | 100,000 | $22/month | ~30–35 sessions |
| Pro | 500,000 | $99/month | ~150–180 sessions |
| Scale | 2,000,000 | $330/month | ~600+ sessions |

Each session generates ~3,000–5,000 characters of speech text.

---

## Features Currently Implemented

### Core Teaching Engine
- [x] Multi-personality AI tutor (7 personalities: strict, very_friendly, attentive, funny, motivational, patient, storyteller)
- [x] Mood-adaptive teaching (7 moods: very_focused, focused, light, non_attentive, tired, curious, exam_prep)
- [x] 5 study levels (beginner → expert) with level-specific instruction depth
- [x] Dynamic system prompt composition (11+ prompt layers assembled per session)
- [x] Session evaluation prompt — AI analyzes student inputs to generate structured teaching plan
- [x] Teaching stream prompt — context-rich prompt for real-time SSE segment delivery
- [x] Goodbye prompt — personalized farewell messages summarizing session achievements
- [x] AI-driven segment planning with structured teaching flow
- [x] Lazy/progressive segment generation — only first segment content generated at session creation, rest on demand
- [x] On-demand segment content generation API (`POST /sessions/{id}/segments/{order}/generate`)
- [x] Real-time teaching stream via SSE (`GET /sessions/{id}/segments/{order}/stream`) — character-by-character AI text streaming with session_end and error events
- [x] User material integration — uploaded PDFs/documents extracted and injected into teaching prompts
- [x] File upload auto-processing — PDF (PyMuPDF), DOCX (python-docx), TXT, images (OCR) text extraction on upload

### Speech & Voice System
- [x] Speech-first prompt instructions (LLM writes for spoken delivery, not reading)
- [x] Emotion markers in LLM output (`[excited]`, `[calm]`, `[encouraging]`, `[warm]`, `[curious]`, `[serious]`)
- [x] Pause control markers (`<pause:200ms>` through `<pause:1500ms>`)
- [x] Teaching rhythm pattern (Hook → Pause → Explanation → Example → Check)
- [x] Conversational fillers in prompt instructions ("So basically...", "Right?", "Now here's the thing...")
- [x] Sentence length optimization (prompts enforce ≤15 words per sentence)
- [x] Voice personality profiles (7 tuned ElevenLabs voice_settings presets per personality)
- [x] Dynamic voice parameters (stability, style, speed, similarity_boost computed from personality × emotion × energy × mood)
- [x] Segment-based energy control (HIGH for intros/celebrations, MEDIUM for teaching, LOW for recaps)
- [x] Mood-based speed modulation (tired students get slower delivery, focused students get slightly faster)
- [x] Speech script processor (parses markers → structured chunks with per-chunk voice parameters)
- [x] Enriched TTS synthesis (voice parameters vary per sentence based on emotional context)
- [x] Streaming TTS with dynamic voice settings
- [x] ElevenLabs multilingual v2 model support

### Session Management
- [x] Multi-profession session creation — adapts required fields per `user_profession` (Student, College Student, Working Professional, Competitive Exams)
- [x] Two-phase session creation — create (AI evaluation, status: `draft`) → preview/edit → start (builds segments)
- [x] AI session evaluation — on creation, AI analyzes inputs and generates structured `session_evaluation` JSON (recommended segments, duration, difficulty, teaching approach)
- [x] Session preview API — frontend can retrieve and edit the AI evaluation before starting
- [x] Full session lifecycle (draft → in_progress → paused → completed/cancelled/ended)
- [x] Session playlists (multi-session learning sequences)
- [x] Mid-session configuration changes (mood, personality, speed, voice)
- [x] AI-determined or user-defined session duration
- [x] Time management instructions in prompts
- [x] Auto session end — triggers when all segments complete or duration exceeded, generates AI goodbye message
- [x] Manual session end — `POST /sessions/{id}/end` with personalized AI goodbye

### Interaction System
- [x] Hand-raise acknowledgement with human-like responses (10+ varied templates)
- [x] Text + image doubt submission with OCR extraction
- [x] AI-powered doubt resolution with context-aware responses
- [x] Real-time chat via WebSocket and REST
- [x] MCQ generation and assessment (with automatic pulse impact: correct +12, incorrect -3)
- [x] Activity-based pulse meter — user activities auto-adjust engagement percentage (doubt +8, chat +5, hand raise +10, MCQ +12/-3, go ahead +3, config change +2, inactivity -10)
- [x] Frontend-triggered pulse adjustments — direct delta API (clamped -50 to +50)
- [x] Pulse percentage tracking (0–100%, default 50%) with threshold-based attention status
- [x] Low-pulse intervention responses

### Content Generation
- [x] AI-generated session segments with teaching scripts
- [x] Smart caching — identical concept + level combos skip AI regeneration
- [x] Session notes generation (Markdown with key points, formulas, diagrams)
- [x] PDF export of session notes
- [x] Visual/animation cue markers in content (`[ANIMATION: ...]`, `[WHITEBOARD: ...]`)
- [x] Whiteboard engine — structured JSON instruction format (text, formulas, diagrams, code, tables, steps)
- [x] Synchronized whiteboard timeline API (`GET /content/{id}/whiteboard-timeline`)
- [x] Whiteboard cue parser — extracts instructions from teaching script markers

### Authentication & Users
- [x] JWT access + refresh token authentication with JTI-based tracking
- [x] Secure logout via Redis-based token blacklisting (JTI invalidation with TTL)
- [x] Registration with password strength validation
- [x] Password change
- [x] User profile CRUD
- [x] Account deactivation
- [x] User type categorization (school_student, college_student, competitive_exam, working_professional, self_learner)
- [x] Two-Factor Authentication (TOTP) — setup, QR code generation, confirm, disable endpoints
- [x] pyotp-based TOTP with 30-second window and ±1 step drift tolerance

### Curriculum Management
- [x] Dual-path curriculum: School (Board → Class/Standard → Subject → Chapter → Topic) and College (University → Course/Degree → Semester → Subject → Chapter → Topic)
- [x] Board type classification (school, university, competitive_exam)
- [x] Semester-based filtering for college subjects
- [x] Full CRUD for boards, subjects, chapters, topics (create + read)
- [x] Question bank management
- [x] Voice profile management

### Infrastructure
- [x] Standard API response envelope (`{success, message, data, error}`)
- [x] Global exception handlers (custom, HTTP, validation, unhandled)
- [x] Request logging middleware
- [x] Rate limiting via slowapi
- [x] Redis caching for segment reuse
- [x] Alembic database migrations
- [x] WebSocket connection manager
- [x] CORS configuration
- [x] 114 automated tests (all passing)

---

## Features NOT Yet Implemented (Backend)

These features require backend work and have no external service limitation preventing implementation.

### 1. Email & OTP Verification
**Status:** Code stubs exist (`EMAIL_SERVICE_ENABLED=false`, `OTP_SERVICE_ENABLED=false`), but no email sending integration.
**Impact:** Users can register without email verification. Password reset requires manual DB intervention.
**Effort:** ~2 days. Add SendGrid/AWS SES SDK.

### 2. Cross-Session Memory (Learning History)
**Status:** Each session has its own interaction history. No cross-session memory.
**Impact:** The tutor doesn't remember what a student struggled with in previous sessions.
**Approach:** Use pgvector (PostgreSQL extension) to embed session summaries. At session start, retrieve relevant past context and inject into system prompt.
**Effort:** ~1 week.

### 3. User Analytics & Learning Progress Aggregation
**Status:** Pulse metrics are stored per-session, but there's no aggregation, trend analysis, or backend aggregation endpoints.
**Impact:** No visibility into long-term learning effectiveness.
**Effort:** ~1 week (backend aggregation endpoints).

### 4. Admin Panel / Admin Endpoints
**Status:** No admin interface for managing curriculum, users, voice profiles, or monitoring system health.
**Impact:** All management requires direct database access or authenticated user endpoints.
**Effort:** ~2-3 weeks.

### 5. Payment & Subscription
**Status:** Not implemented.
**Impact:** No monetization mechanism.
**Effort:** ~1-2 weeks with Stripe/Razorpay integration.

### 6. Multi-Language Curriculum Content
**Status:** The LLM can teach in any language via the `language` parameter, but curriculum data (boards, subjects, chapters) is English-only in the DB.
**Impact:** Non-English-speaking users can get verbal instruction in their language but structured curriculum is English.
**Effort:** ~1 week (add translation column or separate locale tables).

### 7. Voice Cloning / Custom Voices
**Status:** Uses ElevenLabs pre-made voices only.
**Impact:** Cannot create unique tutor voices or match specific accent/gender preferences beyond what ElevenLabs offers.
**Limitation:** ElevenLabs Voice Cloning requires higher-tier plan and consent mechanisms.

### 8. WebSocket Scaling (Multi-Instance)
**Status:** ConnectionManager is in-memory — doesn't work across multiple server instances.
**Impact:** WebSocket connections break when scaling horizontally.
**Approach:** Redis Pub/Sub for cross-instance messaging.
**Effort:** ~2-3 days.

---

## Frontend Dependencies — Features Waiting on Frontend

These features have **complete or near-complete backend support** but require a frontend application to become functional for end users. The backend APIs, data structures, and generation pipelines are in place.

### 1. Real-Time Animation Rendering
**Backend status:** ✅ Complete — generates animation cue markers (`[ANIMATION: type=diagram, description=...]`), stores `AnimationData` records with `animation_spec`, `trigger_timestamp_seconds`, and `sync_text`.
**Frontend needed:** A rendering engine (Lottie, Mermaid.js, D3.js, KaTeX) that reads animation specs and renders them on a canvas/DOM synchronized with audio.
**API endpoints:** `POST /content/{id}/generate`, `GET /content/{id}`

### 2. Whiteboard Rendering & Sync
**Backend status:** ✅ Complete — generates structured whiteboard instructions (write_text, write_formula, draw_diagram, code_block, table, step-by-step reveals). The `GET /content/{id}/whiteboard-timeline` endpoint returns timed instruction sets per segment.
**Frontend needed:** A canvas/whiteboard component (HTML5 Canvas, Excalidraw, or custom SVG) that reads the instruction timeline and renders content synchronized with the audio player.
**API endpoints:** `GET /content/{id}/whiteboard-timeline`

### 3. Audio Playback with Pause Synchronization
**Backend status:** ✅ Complete — generates pause markers (`<pause:400ms>`) and per-chunk audio segments with `pause_after_ms`. Speech processor splits scripts into timed chunks with individual voice parameters.
**Frontend needed:** A custom Web Audio API player that plays chunks sequentially, inserts programmatic silence between chunks, and emits sync events to the animation/whiteboard layers.
**API endpoints:** `POST /speech/process`, `POST /voices/{id}/synthesize`

### 4. Frontend Application
**Backend status:** ✅ Complete — all REST + WebSocket APIs functional at `/api/v1/`.
**Frontend needed:** A full web application (recommended: Next.js 14+ with TypeScript). Key pages: login, multi-step session creation wizard (adapts fields per profession), session preview/edit, live session (SSE text stream + TTS + whiteboard + animation), pulse meter widget, notes viewer, dashboard, curriculum browser.
**Estimated effort:** 4-8 weeks for MVP.

### 5. SSE Real-Time Teaching Stream UI
**Backend status:** ✅ Complete — `GET /sessions/{id}/segments/{order}/stream` returns Server-Sent Events with character-by-character AI teaching text, session_end events, and error events.
**Frontend needed:** An EventSource client that connects to the SSE endpoint, displays streaming text in a typewriter-style UI, handles segment transitions, and triggers audio synthesis on completed sentences. Should integrate with the pulse meter widget and animation layer.
**API endpoints:** `GET /sessions/{id}/segments/{order}/stream`

### 6. Multi-Profession Session Creation Wizard
**Backend status:** ✅ Complete — `POST /sessions` validates different required fields per `user_profession` (Student: board/grade/subject, College Student: university/course/semester, Working Professional: professional_background, Competitive Exams: board). Returns `session_evaluation` JSON for preview.
**Frontend needed:** A multi-step creation wizard that: (1) asks user profession, (2) shows relevant fields, (3) submits and displays AI evaluation preview, (4) allows editing the evaluation, (5) starts the session. Should include the profession-specific field validation matching backend schema.
**API endpoints:** `POST /sessions`, `GET /sessions/{id}/preview`, `PUT /sessions/{id}/evaluation`, `POST /sessions/{id}/start`

### 7. Pulse Meter Widget
**Backend status:** ✅ Complete — activity-based pulse with automatic deltas, frontend-triggered adjust API, and GET endpoint for current state.
**Frontend needed:** A real-time gauge or progress bar (0–100%) with color coding (green > 70%, yellow 40–70%, red < 40%). Should update on every interaction (doubt, chat, hand raise, MCQ answer). Include an inactivity timer that sends `-10` delta after 2 minutes of no interaction. Optionally show recent activity history.
**API endpoints:** `POST /interactions/pulse/{id}/adjust`, `POST /interactions/pulse/{id}/activity`, `GET /interactions/pulse/{id}`

### 8. Analytics Dashboard
**Backend status:** Partial — pulse metrics stored per-session. Needs aggregation endpoints (backend Task #3 above), then frontend chart rendering.
**Frontend needed:** Chart.js or Recharts dashboard for learning progress, pulse trends, topic mastery.

### 9. Admin Panel UI
**Backend status:** Partial — CRUD endpoints exist for curriculum but not for admin-specific operations (user management, system monitoring).
**Frontend needed:** Admin interface for managing boards/subjects/chapters/topics, user accounts, voice profiles, and system health monitoring.

---

## Limitations & Constraints

### AI Response Quality
- **Hallucination Risk:** LLMs can generate incorrect information, especially for niche or advanced topics. No fact-checking layer exists.
- **Token Limits:** Very long sessions may exceed context windows. The system doesn't implement conversation truncation or summarization for long chats.
- **Latency:** Each AI call takes 2–8 seconds. ~~Multiple segment generation at session start can take 15–30 seconds.~~ **Mitigated:** Lazy segment generation now only generates the first segment at session creation. Subsequent segments are generated on demand, reducing session creation time to ~3-5 seconds.

### Voice / TTS
- **Single Voice per Session:** Voice ID is set at session creation. Dynamic mid-session voice switching is not supported by ElevenLabs without separate API calls.
- **ElevenLabs Rate Limits:** Free/lower tiers have strict character limits. Production usage requires Scale plan.
- **Emotion in Voice:** While we compute dynamic voice parameters (stability, style, speed), ElevenLabs' ability to express genuine emotion is limited. The difference between `[excited]` and `[calm]` is subtle — mostly speed and stability shifts, not true emotional prosody.
- **Streaming Latency:** First byte of TTS audio takes 500ms–2s from ElevenLabs.

### Database
- **No Read Replicas:** Single database instance. High traffic will bottleneck on DB.
- **No Sharding:** All data in one database. Multi-region deployment requires database replication.
- **Session Cache:** Redis stores segment plans for reuse, but cache invalidation is hash-based (concept + level + type) — minor prompt changes won't invalidate.

### Security
- **JWT Blacklisting:** ✅ Implemented — Redis-based JTI blacklist for secure logout. Tokens invalidated with TTL matching remaining expiry.
- **2FA:** ✅ Implemented — TOTP-based two-factor authentication with pyotp.
- **File Upload Security:** MIME type and extension validation exists, but no virus scanning.

### Scale
- **Single Process:** Uvicorn runs single-worker by default. Production needs Gunicorn with multiple workers.
- **No CDN:** Audio files and PDFs served directly from the application server.
- **WebSocket:** ConnectionManager is in-memory — doesn't work across multiple server instances without a message broker (Redis Pub/Sub).

---

## Solutions, Approaches & Cost Estimates

### 1. Email & OTP Integration

**Best Solution:** SendGrid or AWS SES

| Approach | Cost | Complexity | Recommendation |
|---|---|---|---|
| SendGrid | Free: 100 emails/day, Essentials: $19.95/mo for 50K | Low | **Best for startups** |
| AWS SES | $0.10 per 1,000 emails | Low | Best for scale |
| Resend | Free: 100/day, Pro: $20/mo | Low | Best DX |

**Implementation:** ~2 days. Add `aiosmtplib` or `sendgrid` SDK. Wire into registration flow and password reset.

### 2. Frontend Application

**Best Solution:** Next.js 14+ with TypeScript

| Approach | Cost | Complexity | Recommendation |
|---|---|---|---|
| Next.js + Tailwind + Framer Motion | Hosting: $0–20/mo (Vercel) | High | **Best for this project** |
| React + Vite | Hosting: $0–5/mo | Medium | Simpler but less SEO |
| Flutter Web | Free tooling | High | If mobile-first |

**Implementation:** ~4–8 weeks for MVP. Key pages: login, session creation, live session (TTS + animation), notes viewer, dashboard.

### 3. Real-Time Animation & Visual Stimulation

> **This is the most important and most challenging feature for the entire project.**

**The Problem:** The backend generates text markers like `[ANIMATION: type=diagram, description="show photosynthesis process with chloroplast"]`, but there is no system to turn these into actual visual content the student sees.

**Approaches ranked by quality:**

#### Option A: AI-Generated Animations (Best Quality, Highest Cost)

Use **Manim** (3Blue1Brown's animation engine) + custom renderer.

| Component | Technology | Cost |
|---|---|---|
| Animation scripting | Manim Community Edition | Free (open-source) |
| LLM generates Manim code | GPT-4o generates Python/Manim scripts from cue descriptions | ~$0.02/animation |
| Server-side rendering | FFmpeg + headless GPU rendering | GPU server: $50–200/mo |
| Pre-rendered library | Build a library of common animations, indexed by topic keywords | One-time ~$500–2000 in compute |
| Delivery | Stream MP4/WebM to frontend | CDN: ~$0.02/GB |

**Total: $100–400/month + one-time library build cost**
**Pros:** Beautiful, professional-grade animations. Unique differentiator.
**Cons:** Complex pipeline. LLM-generated Manim code may have errors. Rendering latency.

#### Option B: Pre-Built Animation Library + Keyword Matching (Best Balance)

Build a curated library of animations for common STEM topics, tagged by concept/keyword. Backend matches animation cues to library entries.

| Component | Technology | Cost |
|---|---|---|
| Animation library | Lottie (JSON animations) + custom SVG animations | Design: $2000–5000 one-time |
| Matching engine | Semantic search (embed cue descriptions, match to library) | Minimal |
| Whiteboard | Excalidraw-based canvas (open-source) | Free |
| Fallback | Auto-generated diagrams via Mermaid.js or D3.js | Free |
| Frontend player | Lottie-React + CSS animations | Free |

**Total: $2000–5000 one-time + minimal ongoing**
**Pros:** Fast, reliable, no rendering latency. Consistent quality.
**Cons:** Limited to pre-built animations. New topics need new animations.

#### Option C: Generative Image + Simple Animation (Quick Win)

Use AI image generation for static visuals, with CSS/JS transitions.

| Component | Technology | Cost |
|---|---|---|
| Image generation | DALL-E 3 or Stable Diffusion XL | DALL-E: $0.04/image, SD: self-hosted ~$50/mo |
| Diagram generation | Mermaid.js from structured prompts | Free |
| Simple animations | CSS transitions + GSAP/Framer Motion | Free |
| Math rendering | KaTeX or MathJax | Free |

**Total: $50–150/month**
**Pros:** Quick to implement. Flexible — works for any topic.
**Cons:** Static images aren't true animations. Quality inconsistent from AI generation.

#### Recommended Approach: **Option B + Option C Hybrid**
- Use a pre-built Lottie animation library for the top 50–100 most common concepts
- Use Mermaid.js for flowcharts, diagrams, and process flows (generated from LLM structured output)
- Use KaTeX for math rendering
- Use Excalidraw for whiteboard interactions
- Use DALL-E 3 as fallback for concepts without pre-built animations
- Add Manim pipeline later as a premium feature

**Estimated total: $3000–6000 one-time + $50–100/month ongoing**

### 4. Audio Player with Pause Synchronization

**Best Solution:** Custom Web Audio API player

The backend already returns `{audio: bytes, pause_after_ms: int}` per speech chunk. The frontend needs:
- Audio queue that plays chunks sequentially
- Programmable silence insertion between chunks (using `AudioContext`)
- Sync events emitted to animation layer (so visuals change at the right moment)

| Component | Technology | Cost |
|---|---|---|
| Audio player | Web Audio API + Howler.js | Free |
| Pause insertion | `AudioContext.createBufferSource` + delay scheduling | Free |
| Sync events | Custom event emitter tied to audio timeline | Free |

**Implementation:** ~1–2 weeks frontend work. No additional cost.

### 5. Cross-Session Memory

**Best Solution:** Vector database for conversation embedding

| Approach | Cost | Complexity |
|---|---|---|
| Pinecone | Free: 100K vectors, $70/mo starter | Medium |
| Weaviate (self-hosted) | Free + hosting ~$20/mo | Medium |
| pgvector (PostgreSQL extension) | Free (already using PG) | **Low — Recommended** |

Use `pgvector` to embed student interaction summaries. At session start, retrieve relevant past context and inject into the system prompt.

**Implementation:** ~1 week. Add `pgvector` extension, embed session summaries with OpenAI embeddings ($0.0001/1K tokens), retrieve top-K similar interactions.

### 6. Token Blacklisting / Secure Logout

**✅ IMPLEMENTED** — Redis-based JWT blacklist.

JTIs (JWT IDs) are now included in every token. On logout, the JTI is stored in Redis with a TTL matching the token's remaining lifetime. The `get_current_user` dependency can check the blacklist before granting access.

**Cost:** Free (already using Redis). Zero additional infrastructure.

### 7. Analytics & Learning Dashboard

**Best Solution:** Aggregate pulse data + session metadata

| Component | Approach | Cost |
|---|---|---|
| Backend aggregation | New API endpoints: weekly pulse trends, topic mastery, time spent | Free |
| Dashboard | Chart.js or Recharts on the frontend | Free |
| Advanced analytics | PostHog (self-hosted) or Mixpanel | Free tier available |

**Implementation:** ~1 week backend + 1 week frontend.

### 8. WebSocket Scaling

**Best Solution:** Redis Pub/Sub for cross-instance messaging

Replace in-memory `ConnectionManager` with Redis Pub/Sub channel per session. Use `broadcaster` library for async pub/sub.

| Approach | Cost |
|---|---|
| Redis Pub/Sub (already have Redis) | Free |
| NATS / RabbitMQ | Self-hosted: free + $10–20/mo hosting |

**Implementation:** ~2–3 days.

### 9. File Content Extraction

**✅ IMPLEMENTED** — Full document processing pipeline.

| Format | Library | Status |
|---|---|---|
| PDF → text | PyMuPDF (fitz) | ✅ Implemented |
| DOCX → text | python-docx | ✅ Implemented |
| TXT → text | Built-in | ✅ Implemented |
| Image → text (OCR) | pytesseract | ✅ Implemented |

Files are auto-extracted on upload (`POST /materials/upload`). Extracted content is stored in `UserMaterial.extracted_content` and fed into session teaching prompts when material_ids are provided at session creation.

### 10. 2FA / Multi-Factor Authentication

**✅ IMPLEMENTED** — TOTP-based 2FA.

| Component | Technology | Status |
|---|---|---|
| TOTP generation | pyotp (TOTP, 30s window) | ✅ Implemented |
| QR code generation | qrcode library (PNG, base64) | ✅ Implemented |
| Setup flow | `POST /users/me/2fa/setup` → QR code → `POST /users/me/2fa/confirm` | ✅ Implemented |
| Disable flow | `POST /users/me/2fa/disable` (requires valid TOTP code) | ✅ Implemented |

**Cost:** Free (pyotp + qrcode are open-source).

---

## Animation & Visual Stimulation — The Main Challenge

This section serves as a deep dive into the **most critical missing feature**: real-time visual stimulation synchronized with the AI tutor's speech.

### Why This Matters

The AI tutor describes concepts verbally and includes animation markers in its output. But without visual rendering, the student is essentially listening to a podcast. Research shows that **visual + auditory learning** improves retention by 65% compared to audio-only instruction (Mayer's Multimedia Learning Theory).

### Current Backend Output

When the LLM teaches, it produces markers like:

```
[ANIMATION: type=process_animation, description="Show water molecule breaking into hydrogen and oxygen through electrolysis"]
[WHITEBOARD: action=write, content="H₂O → H₂ + O₂"]
[ANIMATION: type=diagram, description="Display the structure of a chloroplast with thylakoid membranes highlighted"]
```

These markers are structured data ready for a rendering engine. The backend work is done — the frontend rendering is the gap.

### Recommended Architecture

```
LLM Output → Speech Processor → TTS (with pauses)
                ↓
         Animation Cue Parser → Cue Matcher → Renderer
                                    ↓              ↓
                            Pre-built Library   AI Fallback
                            (Lottie/SVG/CSS)   (Mermaid/DALL-E)
```

### Animation Type → Rendering Technology Map

| Animation Type | Best Renderer | Fallback | Latency |
|---|---|---|---|
| `diagram` | Pre-built SVG library | Mermaid.js auto-generated | <100ms / 1–2s |
| `flowchart` | Mermaid.js | D3.js force-directed graph | 1–2s |
| `process_animation` | Lottie (pre-built) | CSS keyframe sequence | <100ms / 200ms |
| `timeline` | CSS + Framer Motion | Mermaid.js gantt chart | 200ms |
| `math_visualization` | KaTeX + custom SVG | MathJax | <100ms |
| `code_walkthrough` | Prism.js + highlight animation | Monaco Editor readonly | <100ms |
| `real_world_analogy` | DALL-E 3 generated image | Stock image match | 3–5s / 500ms |
| `comparison` | Side-by-side CSS grid + animation | HTML table | 200ms |
| `hierarchy` | D3.js tree layout | ASCII tree | 500ms |
| `network_graph` | D3.js force-directed | vis.js | 500ms |

### Synchronization Strategy

1. Backend returns speech chunks with `pause_after_ms` between each
2. Backend returns animation cues with `segment_order` identifying when they appear
3. Frontend audio player emits `chunk_start` and `chunk_end` events
4. Animation controller listens for events and triggers corresponding visuals
5. Longer pauses (700ms–1500ms) are used specifically for animation transitions

### Cost Summary for Full Animation System

| Component | One-Time Cost | Monthly Cost |
|---|---|---|
| Lottie animation library (50–100 concepts) | $3,000–5,000 | — |
| Mermaid.js integration | $0 (open source) | — |
| KaTeX math rendering | $0 (open source) | — |
| Excalidraw whiteboard | $0 (open source) | — |
| DALL-E 3 fallback images | — | $50–150 |
| CDN for animation assets | — | $5–20 |
| Frontend development | $5,000–15,000 | — |
| **Total** | **$8,000–20,000** | **$55–170** |

---

## Infrastructure Recommendations

### Development
- Local PostgreSQL + Redis
- `.env` file with test API keys
- `uvicorn app.main:app --reload`

### Staging
| Service | Provider | Cost |
|---|---|---|
| App Server | Railway / Render | $5–25/mo |
| PostgreSQL | Supabase / Neon | Free tier |
| Redis | Upstash | Free tier |
| Domain + SSL | Cloudflare | Free |

### Production
| Service | Provider | Cost |
|---|---|---|
| App Server (2+ workers) | AWS EC2 t3.medium or Fly.io | $30–80/mo |
| PostgreSQL (managed) | AWS RDS or Supabase Pro | $25–50/mo |
| Redis (managed) | AWS ElastiCache or Upstash | $15–30/mo |
| CDN | CloudFront or Cloudflare | $5–20/mo |
| GPU (for Manim, optional) | RunPod or Vast.ai | $50–200/mo |
| Monitoring | Sentry (free tier) + Grafana Cloud (free tier) | $0 |
| **Total (without animation GPU)** | | **$75–180/mo** |
| **Total (with animation GPU)** | | **$125–380/mo** |

### Production at Scale (1000+ concurrent students)
| Service | Provider | Cost |
|---|---|---|
| App Server (auto-scaling) | AWS ECS Fargate or K8s | $200–500/mo |
| PostgreSQL (multi-AZ) | AWS RDS r6g.large | $200–400/mo |
| Redis Cluster | AWS ElastiCache | $100–200/mo |
| Load Balancer | AWS ALB | $20/mo |
| OpenAI API | — | $500–2000/mo |
| ElevenLabs Scale | — | $330/mo |
| CDN | CloudFront | $50–100/mo |
| **Total** | | **$1,400–3,550/mo** |

---

## Quick Reference: What to Build Next (Priority Order)

| Priority | Feature | Effort | Impact | Status |
|---|---|---|---|---|
| 🔴 P0 | Frontend application (Next.js) | 4–8 weeks | Enables the entire product | ❌ Not started |
| 🔴 P0 | SSE teaching stream UI | 1 week | Real-time text display | ⏳ Backend ready |
| 🔴 P0 | Multi-profession session wizard | 1 week | Full session creation flow | ⏳ Backend ready |
| 🔴 P0 | Audio player with pause sync | 1–2 weeks | Makes TTS sound human | ⏳ Backend ready |
| 🔴 P0 | Whiteboard / animation rendering (Canvas) | 2–3 weeks | Visual learning starts | ⏳ Backend ready |
| 🔴 P0 | Pulse meter widget | 3 days | Engagement visibility | ⏳ Backend ready |
| 🟠 P1 | Email verification | 2 days | Security requirement | ❌ Not started |
| 🟠 P1 | Cross-session memory (pgvector) | 1 week | Personalized learning | ❌ Not started |
| 🟠 P1 | Lottie animation library (top 50 concepts) | 2–4 weeks | Rich visual experience | ❌ Not started |
| 🟡 P2 | Analytics dashboard | 2 weeks | Learning progress visibility | ❌ Not started |
| 🟡 P2 | WebSocket Redis Pub/Sub | 3 days | Multi-instance deployment | ❌ Not started |
| 🟢 P3 | Admin panel | 2–3 weeks | Operational management | ❌ Not started |
| 🟢 P3 | Payment integration | 1–2 weeks | Monetization | ❌ Not started |
| 🟢 P3 | Manim animation pipeline | 3–4 weeks | Premium visual quality | ❌ Not started |
| ✅ Done | Multi-profession session creation | — | Tailored user experience | ✅ Implemented |
| ✅ Done | AI session evaluation & preview | — | Smart session planning | ✅ Implemented |
| ✅ Done | SSE real-time teaching stream | — | Live teaching delivery | ✅ Implemented |
| ✅ Done | Activity-based pulse meter | — | Engagement tracking | ✅ Implemented |
| ✅ Done | Auto/manual session end + AI goodbye | — | Clean session closure | ✅ Implemented |
| ✅ Done | 2FA authentication | — | Security hardening | ✅ Implemented |
| ✅ Done | Token blacklisting (logout) | — | Security | ✅ Implemented |
| ✅ Done | File content extraction | — | Material processing | ✅ Implemented |
| ✅ Done | Lazy segment generation | — | Latency + cost reduction | ✅ Implemented |
| ✅ Done | Whiteboard engine (backend) | — | Visual sync instructions | ✅ Implemented |
| ✅ Done | Curriculum CRUD + dual-path | — | School/college support | ✅ Implemented |
