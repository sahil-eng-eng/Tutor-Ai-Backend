# AI Tutor Platform

A comprehensive backend system for a human-like AI tutoring experience. Built with FastAPI, PostgreSQL, OpenAI, and ElevenLabs. Designed for real-time, interactive learning sessions with dynamic teaching, doubt clearing, pulse monitoring, and rich content generation.

---

## Features

### Humanly AI Tutor
- **7 Personality modes** — strict, very_friendly, attentive, funny, motivational, patient, storyteller
- **7 Mood adaptations** — very_focused, focused, light, non_attentive, tired, curious, exam_prep
- **5 Study levels** — beginner through expert with calibrated depth and vocabulary
- **Age-aware language** — adjusts tone for school kids, teens, college students, professionals
- **Curiosity triggers & stories** — naturally woven into teaching to maintain engagement
- **Celebration responses** — positive reinforcement when students answer correctly

### Session Management
- **Multi-profession support** — session creation adapts required fields based on `user_profession`: Student (board, grade, subject), College Student (university, course, semester), Working Professional (professional_background), Competitive Exams (exam type via board)
- **Two-phase creation** — create (AI evaluates inputs, generates `session_evaluation` JSON, status: `draft`) → preview → edit evaluation → start (builds segments, generates first content)
- **AI session evaluation** — on creation, AI analyzes the student's inputs and generates a structured evaluation with recommended segments, duration estimate, difficulty assessment, and teaching approach
- **Configurable sessions** — topic, subject, study level, session type, mood, personality, language, voice
- **Duration modes** — user-defined or AI-determined (max 3 hours)
- **Session lifecycle** — create (draft) → start (in_progress) → pause → resume → complete/cancel/end
- **Segment-based teaching** — AI generates ordered segments (introduction, explanation, examples, practice, summary)
- **Lazy segment generation** — segments are built from `session_evaluation` at start time; only segment 1 content is generated upfront; subsequent segments generated on-demand via API
- **Real-time teaching stream (SSE)** — Server-Sent Events endpoint streams AI-generated teaching text character-by-character for live display
- **Auto/manual session end** — sessions auto-end when all segments are completed or duration is exceeded; manual end via API triggers an AI-generated personalized goodbye message
- **Material injection** — sessions accept `material_ids` at creation time; extracted file text is injected into the AI teaching context
- **Mid-session config changes** — switch mood, personality, or speed without restarting
- **Playlist mode** — chain multiple sessions for in-depth topic coverage
- **Session caching** — SHA-256 concept hashing to reuse segment plans, reducing API costs

### Real-Time Interaction (WebSocket)
- **Hand raise** — pause the tutor instantly with natural acknowledgement
- **Live doubt clearing** — text and OCR-based doubt submission with AI resolution
- **Go ahead button** — resume teaching after doubt resolution
- **Chat** — ask questions during the session
- **Config changes** — adjust settings mid-session via WebSocket

### Pulse Meter (Activity-Based Engagement Tracking)
- **Activity-driven deltas** — user activities automatically adjust pulse: doubt (+8), chat (+5), hand raise (+10), MCQ correct (+12), MCQ incorrect (-3), go ahead (+3), config change (+2), inactivity (-10)
- **Frontend-triggered adjustments** — direct pulse delta API for custom UI interactions (clamped -50 to +50)
- **Attention analysis** — threshold-based status (high_attention → low_attention) with pulse percentage (0–100%)
- **MCQ pulse checks** — auto-generated questions when attention drops or pulse falls below threshold
- **Recommendations** — AI suggests breaks, engagement changes, or pace adjustments
- **Real-time pulse widget** — GET endpoint returns current percentage, status, and recent activity history

### Content & Visuals
- **Animation generation** — 11 types (graph plots, diagrams, flowcharts, mind maps, equations, 3D visualizations, etc.)
- **Whiteboard engine** — zero-cost, zero-latency instruction builder that produces structured drawing objects (text, formulas, diagrams, code blocks, tables) without any AI API call
- **Whiteboard timeline API** — ordered list of all whiteboard events generated so far in a session, used for frontend replay/seek
- **Teaching markers** — `[ANIMATION:]`, `[WHITEBOARD:]`, `[PAUSE:]`, and `[EMOTION:]` embedded in AI output for frontend sync
- **Content timeline** — ordered list of visual events with timestamps

### Notes & Export
- **Session notes** — markdown with key points, formulas, diagrams, and full transcript
- **PDF generation** — downloadable PDF via ReportLab
- **Automatic transcription** — full session dialogue captured

### OCR & Materials
- **Image OCR** — pytesseract-based text extraction from uploaded images (handwritten doubts, textbook photos)
- **Document processing** — automatic text extraction on upload for PDF (PyMuPDF), DOCX (python-docx), and plain TXT files; no manual trigger required
- **Material upload** — PDF, DOCX, TXT, and image files; `extracted_content` stored in the database; `processed` flag indicates extraction success
- **User material library** — per-user file management with pagination

### Curriculum Module
- **Hierarchical structure** — Board → Subject → Chapter → Topic
- **Dual-path support** — school mode (Board/Grade system) vs. college mode (University/Semester system) governed by `board_type` field (`school`, `university`, `competitive_exam`)
- **Full CRUD** — admin-level creation endpoints for boards, subjects, chapters, and topics
- **Filtered browsing** — filter boards by `board_type`; filter subjects by `semester` for college paths
- **Question bank** — both predefined and user-created
- **Difficulty levels** — mapped to study levels

### Authentication & Security
- **JWT token blacklisting** — on logout, the token's JTI is added to a Redis-backed blacklist; all protected endpoints reject blacklisted tokens
- **TOTP-based 2FA** — users can enable time-based one-time password authentication; setup returns a QR code URI; confirm step validates first TOTP before activating; disable step requires current password + valid TOTP
- **Secure logout** — `POST /auth/logout` invalidates the current access token immediately
- **Rate limiting** — slowapi enforces per-IP and per-user request limits on all auth and generation endpoints

### AI Model Selection
- **Automatic model routing** — scoring system based on study level + session type + complexity
- **Three tiers** — cheap (GPT-3.5-turbo), standard (GPT-4o-mini), premium (GPT-4o)
- **Task-specific models** — separate selection for doubt resolution and MCQ generation

### Prompt Engineering
- **11-layer prompt composition** — base personality + mood + level + session structure + duration + visual sync + curiosity + student context + age + topic + session type
- **Dynamic prompt assembly** — `compose_system_prompt()` builds the full system prompt per session
- **Session evaluation prompt** — `compose_session_evaluation_prompt()` generates AI analysis of student inputs for session planning
- **Teaching stream prompt** — `compose_session_teaching_prompt()` builds context for real-time segment teaching via SSE
- **Goodbye prompt** — `compose_session_goodbye_prompt()` creates personalized farewell messages on session end
- **Specialized prompts** — doubt resolution, MCQ generation, segment planning, notes generation

---

## Architecture

```
app/
├── main.py                  # FastAPI app factory, health endpoint
├── config.py                # Pydantic Settings (env-based config)
├── database.py              # Async SQLAlchemy engine + session
├── dependencies.py          # Auth dependency (get_current_user)
├── core/
│   ├── security.py          # Password hashing (bcrypt)
│   ├── jwt_handler.py       # JWT create/verify (python-jose)
│   ├── token_blacklist.py   # Redis JTI blacklist for logout/revocation
│   ├── exceptions.py        # Custom exception hierarchy
│   └── rate_limiter.py      # slowapi rate limiter
├── middleware/
│   └── logging_middleware.py # Request duration logging
├── models/                  # SQLAlchemy ORM models
│   ├── user.py              # User + UserType + UserProfession enums
│   ├── session.py           # TutorSession (+ evaluation, profession, pulse), SessionSegment, SessionConfig, SessionPlaylist
│   ├── content.py           # AnimationData, WhiteboardData, SessionNotes
│   ├── interaction.py       # Interaction, PulseMetric, DoubtRecord, MCQQuestion
│   ├── curriculum.py        # Board, Subject, Chapter, Topic, QuestionBank
│   ├── voice.py             # VoiceProfile
│   ├── material.py          # UserMaterial
│   └── cache.py             # SessionCache
├── schemas/                 # Pydantic request/response models
│   ├── user.py, session.py, content.py, interaction.py, curriculum.py
├── prompts/                 # AI prompt templates
│   ├── base_prompts.py      # Core tutor instructions
│   ├── personality_prompts.py  # 7 personality templates
│   ├── mood_prompts.py      # 7 mood adaptations
│   ├── interaction_prompts.py  # Response arrays for interactions
│   ├── level_prompts.py     # 5 study level instructions
│   └── prompt_composer.py   # Multi-layer prompt assembly
├── services/                # Business logic layer
│   ├── auth_service.py      # Registration, login, tokens
│   ├── user_service.py      # Profile CRUD
│   ├── session_service.py   # Full session lifecycle + evaluation + SSE streaming + auto-end + caching
│   ├── ai_tutor_service.py  # OpenAI API integration
│   ├── model_selector_service.py  # Model routing logic
│   ├── content_generation_service.py  # Animations, whiteboards, notes
│   ├── voice_service.py     # ElevenLabs TTS
│   ├── pulse_service.py     # Activity-based pulse meter + MCQ checks
│   ├── doubt_service.py     # Hand raise + doubt resolution
│   ├── curriculum_service.py  # Curriculum CRUD
│   ├── ocr_service.py       # pytesseract OCR
│   ├── document_processor.py  # PDF (PyMuPDF) / DOCX / TXT text extraction
│   ├── totp_service.py      # TOTP secret generation, QR code, verification
│   └── whiteboard_engine.py # Zero-cost whiteboard instruction builders + timeline
├── api/v1/                  # API route handlers
│   ├── router.py            # Main router (includes all sub-routers)
│   ├── auth.py, users.py, sessions.py, interactions.py
│   ├── content.py, curriculum.py, voices.py, materials.py
│   └── websocket.py         # Real-time session WebSocket
└── utils/
    ├── email.py             # Email placeholders
    ├── otp.py               # OTP generation
    ├── pdf_generator.py     # ReportLab PDF export
    └── file_handler.py      # File validation + storage

tests/
├── conftest.py              # Async test fixtures, test DB
├── test_auth.py             # Auth endpoint tests
├── test_users.py            # User profile tests
├── test_sessions.py         # Session lifecycle tests
├── test_interactions.py     # Doubt, pulse, MCQ, chat tests
├── test_content.py          # Content generation tests
├── test_curriculum.py       # Curriculum + voices + materials tests
├── test_prompts.py          # Prompt composition unit tests
├── test_pulse.py            # Pulse service logic tests
├── test_model_selector.py   # Model selection tests
├── test_core.py             # Security, JWT, OTP tests
├── test_websocket.py        # WebSocket protocol tests
├── test_utils.py            # Utility function tests
└── test_health.py           # Health endpoint test
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (async) |
| Database | PostgreSQL + SQLAlchemy Async + asyncpg |
| Cache | Redis (configured) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| AI | OpenAI API (GPT-3.5/4o-mini/4o) via httpx |
| TTS | ElevenLabs API |
| OCR | pytesseract + Pillow |
| Document Processing | PyMuPDF (fitz) + python-docx |
| 2FA / TOTP | pyotp + qrcode[pil] |
| PDF | ReportLab |
| Rate Limiting | slowapi |
| Testing | pytest + pytest-asyncio + httpx |
| Migrations | Alembic |

---

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for caching)
- Tesseract OCR installed on system

### Installation

```bash
# Clone
git clone <repository-url>
cd tutor

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with your database URL, API keys, etc.

# Database migrations
alembic upgrade head

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

See `.env.example` for all required configuration:
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing key
- `OPENAI_API_KEY` — OpenAI API key
- `ELEVENLABS_API_KEY` — ElevenLabs API key
- `REDIS_URL` — Redis connection (optional)

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_prompts.py::TestPromptComposer::test_compose_system_prompt_basic -v
```

---

## API Documentation

Once running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Full API reference:** See [API_README.md](API_README.md)

---

## Design Principles

- **SOLID** — Single responsibility services, dependency injection, interface segregation
- **Layered architecture** — Models → Schemas → Services → Routes
- **Async-first** — All I/O operations are async
- **Cost optimization** — Session caching with concept hashing, tiered model selection
- **Human-like interaction** — Randomized response pools, personality-driven prompts, natural language patterns
- **Separation of concerns** — Prompt system isolated from business logic
- **Security** — JWT auth with Redis blacklisting, TOTP-based 2FA, bcrypt password hashing, rate limiting, input validation, file type/size checks

---

## Session Lifecycle

```
CREATE (draft) ──────────────────────────────────────────────────┐
  └─► [AI evaluates inputs → session_evaluation JSON]            │
       └─► PREVIEW (view/edit evaluation)                        │
            └─► START (in_progress)                              │
                  [Builds segments from evaluation]              │
                  [Generates segment 1 content]                material_ids
                      ↕                                        injected
                    PAUSE                                      into AI context
                      ↓
                COMPLETE / CANCEL / END (with AI goodbye)

During IN_PROGRESS:
  - Teaching streams via SSE (GET /sessions/{id}/segments/{order}/stream)
  - Teaching also available via WebSocket
  - Hand raise → pause → doubt → resolve → go ahead → resume
  - Activity-based pulse meter tracks engagement automatically
  - Pulse adjust API for frontend-triggered delta changes
  - Config changes (mood, personality) applied instantly
  - Animations/whiteboards triggered by AI markers ([ANIMATION:], [WHITEBOARD:])
  - Segment N+1 generated on-demand via POST /sessions/{id}/segments/{order}/generate
  - Auto-end when all segments complete or duration exceeded (AI goodbye message)
  - Manual end via POST /sessions/{id}/end (AI goodbye message)
```

---

## Max Session Duration

Sessions are capped at **3 hours** (180 minutes). For `ai_determined` duration, the AI estimates based on topic complexity, study level, and session type.

---

## License

MIT
