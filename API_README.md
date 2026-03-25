# AI Tutor Platform — API Reference

Complete REST + WebSocket API documentation for the AI Tutor backend.

**Base URL:** `http://localhost:8000/api/v1`  
**Auth:** All 🔒 endpoints require `Authorization: Bearer <access_token>` header.  
**All responses** follow the standard envelope:

```json
{
  "success": true,
  "message": "Human-readable status",
  "data": { ... }
}
```

Error responses:
```json
{
  "success": false,
  "message": "Error description",
  "data": null
}
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Users & Profile](#2-users--profile)
3. [Two-Factor Authentication (2FA)](#3-two-factor-authentication-2fa)
4. [Sessions](#4-sessions)
5. [Session Playlists](#5-session-playlists)
6. [Session Preview & Evaluation](#6-session-preview--evaluation)
7. [Session End Management](#7-session-end-management)
8. [Lazy Segment Generation](#8-lazy-segment-generation)
9. [Real-Time Teaching Stream (SSE)](#9-real-time-teaching-stream-sse)
10. [Interactions — Doubts & Hand Raise](#10-interactions--doubts--hand-raise)
11. [Interactions — Pulse Meter](#11-interactions--pulse-meter)
12. [Interactions — MCQ](#12-interactions--mcq)
13. [Interactions — Chat](#13-interactions--chat)
14. [Content & Visuals](#14-content--visuals)
15. [Whiteboard Timeline](#15-whiteboard-timeline)
16. [Curriculum](#16-curriculum)
17. [Voices](#17-voices)
18. [Materials & File Upload](#18-materials--file-upload)
19. [WebSocket — Real-Time Session](#19-websocket--real-time-session)
20. [User Stats](#20-user-stats)
21. [Error Codes](#21-error-codes)
22. [Appendix: Teaching Content Markers](#appendix-teaching-content-markers)

---

## 1. Authentication

### POST `/auth/register`

**Purpose:** Create a new user account. Returns the user profile and a JWT token pair immediately so the user is logged in right after sign-up.

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "StrongPass123!",
  "full_name": "Jane Doe",
  "user_type": "college_student",
  "age": 20,
  "grade": "3rd Year",
  "board": "University of Delhi",
  "institution": "Delhi College of Engineering",
  "preferred_language": "english"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | ✅ | Valid email address |
| `password` | string | ✅ | Min 8 chars, at least 1 uppercase letter and 1 digit |
| `full_name` | string | ✅ | 2–255 characters |
| `user_type` | enum | ✅ | `school_student`, `college_student`, `working_professional`, `self_learner`, `competitive_exam` |
| `age` | int | ❌ | 5–100. Affects AI language complexity and tone |
| `grade` | string | ❌ | Class/standard (school) or degree year/course (college) |
| `board` | string | ❌ | School board name or university name |
| `institution` | string | ❌ | School or college name |
| `preferred_language` | string | ❌ | Default: `english` |

**Response (201):**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "user": {
      "id": "3d6f8b2a-...",
      "email": "student@example.com",
      "full_name": "Jane Doe",
      "user_type": "college_student",
      "age": 20,
      "grade": "3rd Year",
      "board": "University of Delhi",
      "institution": "Delhi College of Engineering",
      "preferred_language": "english",
      "bio": null,
      "is_active": true,
      "is_verified": false,
      "is_2fa_enabled": false,
      "created_at": "2026-03-17T10:00:00Z",
      "updated_at": "2026-03-17T10:00:00Z"
    },
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
  }
}
```

**Frontend Use Case:** Called when the user submits the Sign Up / Registration form. Store `access_token` in memory and `refresh_token` in secure persistent storage. After registration, redirect to the email verification screen since `is_verified` will be `false`.

---

### POST `/auth/login`

**Purpose:** Authenticate an existing user and return a fresh JWT token pair.

**Request Body:**
```json
{
  "email": "student@example.com",
  "password": "StrongPass123!"
}
```

**Response (200):** Same structure as registration — `user` object + `tokens`.

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { ...UserResponse... },
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
  }
}
```

**Frontend Use Case:** Called when the user submits the Login form. After receiving the response, check `is_2fa_enabled` — if `true`, redirect the user to a TOTP verification screen and hold off on granting app access until the second factor is confirmed. If `false`, proceed to the home/dashboard screen.

---

### POST `/auth/logout` 🔒

**Purpose:** Invalidate the current access token by blacklisting its unique identifier (JTI) in Redis. After this call the token cannot be reused even if it has not yet expired — ensuring true session termination regardless of token expiry time.

**Request:** No body required. Pass the token in the `Authorization: Bearer <token>` header.

**Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully",
  "data": null
}
```

**Frontend Use Case:** Called when the user taps "Logout" from the navigation menu or account settings. After receiving a 200 response, immediately clear all stored tokens from memory and secure storage, then redirect to the login screen. Always call this before clearing tokens — do not just discard tokens client-side, as the server needs to invalidate them.

---

### POST `/auth/verify`

**Purpose:** Verify a user's email address using the token included in the verification link sent to their inbox after registration.

**Request Body:**
```json
{
  "token": "<verification_token_from_email_link>"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `token` | string | ✅ | The raw verification token from the email link's query param |

**Response (200):**
```json
{
  "success": true,
  "message": "Account verified successfully",
  "data": { "is_verified": true }
}
```

**Frontend Use Case:** The deep-link handler for the email verification URL (e.g., `yourapp://verify?token=abc123`). Extract the `token` param from the URL and POST it here. On success, redirect to the onboarding or dashboard screen.

---

### POST `/auth/resend-verification`

**Purpose:** Re-send the verification email link, for cases where the original email was not received or the token expired.

**Request Body:**
```json
{
  "email": "student@example.com"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Verification code resent",
  "data": null
}
```

**Frontend Use Case:** The "Resend Email" button on the email verification screen. Typically shown after a 60-second countdown timer expires, or if the user taps "Didn't receive it?".

---

### POST `/auth/forgot-password`

**Purpose:** Initiate a password reset flow. Generates a secure time-limited reset token and sends an email to the user containing a reset link. Always returns success even if the email is not registered (to prevent email enumeration attacks).

**Request Body:**
```json
{
  "email": "student@example.com"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password reset email sent",
  "data": null
}
```

**Frontend Use Case:** The "Forgot Password?" link on the Login screen. Show a simple email input form. After submitting, display a confirmation message: "If this email is registered, you'll receive a reset link shortly."

---

### POST `/auth/reset-password`

**Purpose:** Reset a user's password using the token from the reset email link. The token is single-use and expires after 1 hour.

**Request Body:**
```json
{
  "token": "<reset_token_from_email_link>",
  "new_password": "NewSecure456!"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `token` | string | ✅ | The reset token extracted from the email link's query param |
| `new_password` | string | ✅ | Minimum 8 characters |

**Response (200):**
```json
{
  "success": true,
  "message": "Password reset successfully",
  "data": null
}
```

**Response (400 — invalid/expired token):**
```json
{
  "success": false,
  "message": "Invalid or expired reset token",
  "data": null
}
```

**Frontend Use Case:** The deep-link handler for the password reset URL (e.g., `yourapp://reset-password?token=xyz`). Show a "New Password" + "Confirm Password" form. On success, redirect to login with a toast: "Password reset successfully."

---

### POST `/auth/refresh`

**Purpose:** Exchange a valid refresh token for a new access token + refresh token pair. Use this to keep the user silently logged in without requiring them to enter credentials again.

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Tokens refreshed",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Frontend Use Case:** Called automatically by an HTTP interceptor when any authenticated API call returns `401 Unauthorized`. Transparently exchange the stored refresh token for a new pair and retry the failed request. If refresh also fails, redirect to login.

---

### POST `/auth/change-password` 🔒

**Purpose:** Change the authenticated user's password. Requires the current password to confirm identity before allowing the change.

**Request Body:**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewSecure456!"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password changed successfully",
  "data": null
}
```

**Frontend Use Case:** The "Change Password" form inside Account Settings → Security. After a successful response, optionally log the user out of all other sessions for security.

---

## 2. Users & Profile

### GET `/users/me` 🔒

**Purpose:** Retrieve the complete profile of the currently authenticated user.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Profile retrieved",
  "data": {
    "id": "3d6f8b2a-...",
    "email": "student@example.com",
    "full_name": "Jane Doe",
    "user_type": "college_student",
    "age": 20,
    "grade": "3rd Year",
    "board": "University of Delhi",
    "institution": "Delhi College of Engineering",
    "preferred_language": "english",
    "bio": "Passionate about machine learning.",
    "is_active": true,
    "is_verified": true,
    "is_2fa_enabled": false,
    "created_at": "2026-03-17T10:00:00Z",
    "updated_at": "2026-03-17T10:00:00Z"
  }
}
```

**Frontend Use Case:** Called on app startup and on the "My Profile" screen to populate user details. Also used to:
- Display the user's name and avatar initials in the navigation header
- Check `is_2fa_enabled` to render the correct Security Settings state
- Check `is_verified` to conditionally show the email verification banner

---

### PUT `/users/me` 🔒

**Purpose:** Update one or more profile fields for the authenticated user. Only fields included in the request body are updated.

**Request Body (all fields optional — send only what changed):**
```json
{
  "full_name": "Jane Smith",
  "age": 21,
  "grade": "4th Year",
  "board": "IIT Delhi",
  "institution": "IIT Delhi",
  "preferred_language": "hindi",
  "bio": "Loves competitive programming."
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Profile updated",
  "data": { ...full UserResponse with updated fields... }
}
```

**Frontend Use Case:** The "Edit Profile" form. When the user taps "Save Changes", send only the modified fields to this endpoint. Refresh the displayed profile with the returned data.

---

### DELETE `/users/me` 🔒

**Purpose:** Soft-deactivate the user's account. Marks the account as inactive but does not permanently delete data.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Account deactivated",
  "data": null
}
```

**Frontend Use Case:** The "Deactivate Account" button in Account Settings, placed behind a confirmation dialog asking "Are you sure? You can reactivate by contacting support."

---

## 3. Two-Factor Authentication (2FA)

2FA uses TOTP (Time-based One-Time Password) — the same standard used by Google Authenticator, Authy, and Microsoft Authenticator. The setup is a 3-step flow: **Setup → Scan QR → Confirm**.

### POST `/users/me/2fa/setup` 🔒

**Purpose:** Begin 2FA enrollment. Generates a unique TOTP secret for the user, returns a QR code image (base64 PNG) and the raw secret for manual entry. The secret is stored on the account but 2FA is NOT enabled yet — the user must confirm with a code via `/2fa/confirm` to finalize.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Scan the QR code with your authenticator app, then confirm with /2fa/confirm",
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "provisioning_uri": "otpauth://totp/AI%20Tutor:student%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=AI%20Tutor",
    "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
}
```

| Field | Description |
|---|---|
| `secret` | Raw TOTP secret for manual entry in authenticator apps |
| `provisioning_uri` | otpauth:// URI (same info as the QR code, readable by apps) |
| `qr_code_base64` | Base64-encoded PNG of the QR code. Render with `<img src="data:image/png;base64,{value}">` |

**Frontend Use Case:** Triggered when the user taps "Enable Two-Factor Authentication" in Security Settings. Display the QR code image on screen with instructions to scan it. Also show the plain `secret` text for users who prefer manual entry. Then show a 6-digit code input and a "Confirm" button that calls `/2fa/confirm`.

---

### POST `/users/me/2fa/confirm` 🔒

**Purpose:** Finalize 2FA setup by verifying that the user successfully scanned the QR code and their authenticator app is generating valid codes. Only after this call is 2FA actually active on the account.

**Request Body:**
```json
{
  "totp_code": "483920"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `totp_code` | string | ✅ | 6-digit TOTP code from the authenticator app |

**Response (200):**
```json
{
  "success": true,
  "message": "2FA enabled successfully",
  "data": {
    "message": "2FA enabled successfully",
    "is_2fa_enabled": true
  }
}
```

**Response (400 — wrong code):**
```json
{
  "success": false,
  "message": "Invalid TOTP code",
  "data": null
}
```

**Frontend Use Case:** Called when the user enters the 6-digit code from their authenticator app and taps "Verify & Enable". Use `data.is_2fa_enabled` to update the Security Settings state. A `true` value means 2FA is now active — show the "Disable 2FA" option.

---

### POST `/users/me/2fa/disable` 🔒

**Purpose:** Disable 2FA on the account. Requires a valid TOTP code to verify the user still has access to their authenticator app, preventing unauthorized disabling of 2FA.

**Request Body:**
```json
{
  "totp_code": "612847"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `totp_code` | string | ✅ | 6-digit TOTP code from the authenticator app |

**Response (200):**
```json
{
  "success": true,
  "message": "2FA disabled successfully",
  "data": {
    "message": "2FA disabled successfully",
    "is_2fa_enabled": false
  }
}
```

**Frontend Use Case:** The "Disable Two-Factor Authentication" button in Security Settings, visible only when `is_2fa_enabled` is `true`. Use `data.is_2fa_enabled` (will be `false`) to revert the Security Settings UI to the "Enable 2FA" option.

---

## 4. Sessions

Sessions are the core learning unit of the platform. The session lifecycle is a multi-step flow:

1. **Create** — User selects profession type and provides topic details. AI evaluates all inputs and generates a `session_evaluation` JSON with structured segment plan, teaching strategy, and estimated durations. Session is created in `draft` status.
2. **Preview** — Frontend displays the session evaluation for the user to review and optionally edit (add/remove segments, adjust durations, change teaching approaches).
3. **Start** — Transitions session to `in_progress`. Builds segment DB rows from the evaluation, generates content for segment 1 only (lazy generation for the rest).
4. **Play** — Frontend plays segments via SSE real-time streaming or pre-generated content scripts.
5. **End** — Session ends automatically when all segments complete or duration is exceeded (AI generates a humanly goodbye), or manually via the end API.

### User Profession Types

Session creation requires a `user_profession` field that drives which additional fields are required:

| Profession | Extra Required Fields | Description |
|---|---|---|
| `student` | `board_id`, `class_name` | School student (10th, 12th, etc.) |
| `college_student` | `university`, `course`, `semester` | University/college student |
| `working_professional` | `professional_background` | Working professional upskilling |
| `competitive_exams` | *(none)* | Preparing for competitive exams |

### POST `/sessions` 🔒

**Purpose:** Create a new AI tutoring session. The AI evaluates all user inputs (profession, topic, level, mood, materials) and generates a comprehensive `session_evaluation` JSON containing: session overview, ordered segment plan with titles/types/durations/key_points/teaching_approaches, and a teaching strategy. Session is created in **`draft`** status — the user must preview and then start it.

**Request Body:**
```json
{
  "user_profession": "college_student",
  "concept_name": "Quadratic Equations",
  "description": "Focus on the discriminant and nature of roots",
  "mood": "focused",
  "model_personality": "very_friendly",
  "language": "english",
  "duration_type": "user_defined",
  "duration_minutes": 45,
  "voice_id": null,
  "session_mode": "single_session",
  "study_level": "intermediate",
  "entire_session_type": "intermediate",
  "university": "MIT",
  "course": "Mathematics 101",
  "semester": 3,
  "board_id": null,
  "class_name": null,
  "subject_id": null,
  "chapter_id": null,
  "topic_id": null,
  "professional_background": null,
  "material_ids": ["material-uuid-1"]
}
```

| Field | Type | Required | Options / Notes |
|---|---|---|---|
| `user_profession` | enum | ✅ | `student`, `college_student`, `working_professional`, `competitive_exams` |
| `concept_name` | string | ✅ | The topic to teach. 2–500 chars |
| `description` | string | ❌ | Specific focus within the topic |
| `mood` | enum | ✅ | `very_focused`, `focused`, `light`, `non_attentive`, `tired`, `curious`, `exam_prep` |
| `model_personality` | enum | ✅ | `strict`, `very_friendly`, `attentive`, `funny`, `motivational`, `patient`, `storyteller` |
| `language` | string | ❌ | Default: `english`. Drives AI teaching language |
| `duration_type` | enum | ✅ | `user_defined` (provide `duration_minutes`) or `ai_determined` |
| `duration_minutes` | int | ❌ | 10–180. Required when `duration_type` is `user_defined` |
| `voice_id` | UUID | ❌ | From `GET /voices`. Null = platform default voice |
| `session_mode` | enum | ✅ | `single_session` or `multiple_sessions` (creates a playlist series) |
| `study_level` | enum | ✅ | `beginner`, `basic`, `intermediate`, `advanced`, `expert` |
| `entire_session_type` | enum | ✅ | `basic_overview`, `revision`, `intermediate`, `exam_focused`, `in_depth` |
| `board_id` | UUID | Conditional | Required for `student` profession |
| `class_name` | string | Conditional | Required for `student` profession (e.g., "10th", "12th") |
| `subject_id` / `chapter_id` / `topic_id` | UUID | ❌ | Link to curriculum nodes |
| `university` | string | Conditional | Required for `college_student` profession |
| `course` | string | Conditional | Required for `college_student` profession |
| `semester` | int | Conditional | Required for `college_student` (1–8) |
| `professional_background` | string | Conditional | Required for `working_professional` |
| `material_ids` | UUID[] | ❌ | User-uploaded materials — extracted text is injected into AI teaching context |

**Response (201):**
```json
{
  "success": true,
  "message": "Session created",
  "data": {
    "id": "a1b2c3d4-...",
    "user_id": "3d6f8b2a-...",
    "user_profession": "college_student",
    "concept_name": "Quadratic Equations",
    "mood": "focused",
    "model_personality": "very_friendly",
    "language": "english",
    "duration_type": "user_defined",
    "duration_minutes": 45,
    "session_mode": "single_session",
    "study_level": "intermediate",
    "entire_session_type": "intermediate",
    "status": "draft",
    "ai_model_used": "gpt-4o-mini",
    "pulse_percentage": 50.0,
    "completion_percentage": 0.0,
    "university": "MIT",
    "course": "Mathematics 101",
    "semester": 3,
    "session_evaluation": {
      "session_overview": {
        "main_concept": "Quadratic Equations",
        "description": "A comprehensive session on quadratic equations focusing on discriminant and nature of roots",
        "target_audience": "College student, Mathematics 101, Semester 3",
        "estimated_total_duration_seconds": 2700,
        "difficulty_rating": 3,
        "prerequisites": ["Basic algebra", "Linear equations"]
      },
      "segments": [
        {
          "segment_order": 1,
          "segment_type": "introduction",
          "title": "Introduction to Quadratic Equations",
          "key_points": ["Definition", "Standard form ax²+bx+c=0"],
          "duration_seconds": 300,
          "teaching_approach": "Start with a warm greeting and overview"
        },
        {
          "segment_order": 2,
          "segment_type": "core_teaching",
          "title": "The Discriminant",
          "key_points": ["b²-4ac formula", "Nature of roots"],
          "duration_seconds": 900,
          "teaching_approach": "Visual explanation with parabola graphs"
        }
      ],
      "teaching_strategy": {
        "personality_approach": "Very friendly and encouraging",
        "mood_adaptation": "Keep energy high, student is focused",
        "engagement_techniques": ["Visual aids", "Analogies", "Practice questions"],
        "language_style": "Clear, conversational English"
      }
    },
    "segments": [],
    "config": { ...SessionConfigResponse... },
    "created_at": "2026-03-17T10:05:00Z",
    "updated_at": "2026-03-17T10:05:00Z"
  }
}
```

**Frontend Use Case:** Called when the user completes the "New Session" form. The form should dynamically show/hide fields based on `user_profession` selection. After receiving the response, navigate to the **Session Preview** screen showing the `session_evaluation` data for the user to review before starting.

---

### GET `/sessions` 🔒

**Purpose:** Retrieve a paginated list of all sessions belonging to the current user.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Items per page (max 100) |

**Response (200):**
```json
{
  "success": true,
  "message": "Sessions retrieved",
  "data": {
    "sessions": [
      {
        "id": "a1b2c3d4-...",
        "concept_name": "Quadratic Equations",
        "subject_name": "Mathematics",
        "status": "completed",
        "study_level": "intermediate",
        "completion_percentage": 100.0,
        "created_at": "2026-03-17T10:05:00Z"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20
  }
}
```

`subject_name` is resolved from the linked `subject_id` via a JOIN — `null` if the session has no linked subject.

**Frontend Use Case:** The "My Sessions" / Session History screen. Renders a scrollable list of past sessions. Use pagination to load more. Display `status`, `concept_name`, `subject_name`, `user_profession`, `pulse_percentage`, `completion_percentage`, and `created_at`. Allow tapping a session to resume it (fetch full details then start).

---

### GET `/sessions/{session_id}` 🔒

**Purpose:** Get full details of a single session including all segments with their current state, and the session config.

**Response (200):**
```json
{
  "success": true,
  "message": "Session retrieved",
  "data": {
    "id": "a1b2c3d4-...",
    "concept_name": "Quadratic Equations",
    "status": "active",
    "completion_percentage": 35.0,
    "segments": [ ...full SegmentResponse array... ],
    "config": { ...SessionConfigResponse... }
  }
}
```

**Frontend Use Case:** When the user resumes a session from history, or when the session player re-initializes after an app restart. Check which segments already have `content_script` generated (non-null) to restore playback state accurately.

---

### POST `/sessions/{session_id}/start` 🔒

**Purpose:** Transition a session from `draft` → `in_progress`. Builds segment DB rows from the `session_evaluation`, generates AI teaching content for segment 1 only (lazy generation for the rest), and records the start timestamp. Must be called after the user has previewed and optionally edited the evaluation.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Session started",
  "data": {
    ...SessionDetailResponse with "status": "in_progress",
    "segments": [
      {
        "segment_order": 1,
        "title": "Introduction to Quadratic Equations",
        "content_script": "Hey! So today we are going to dive into...",
        "status": "pending"
      },
      {
        "segment_order": 2,
        "title": "The Discriminant",
        "content_script": null,
        "status": "not_started"
      }
    ]
  }
}
```

**Frontend Use Case:** Called after the user reviews the session preview and taps "Start Session". After receiving the response, navigate to the session player screen. Begin playing segment 1's `content_script` via TTS, or connect to the SSE streaming endpoint for real-time teaching. Also called when resuming a paused session.

---

### POST `/sessions/{session_id}/pause` 🔒

**Purpose:** Pause an active session, recording the pause point.

**Response (200):**
```json
{
  "success": true,
  "message": "Session paused",
  "data": { ...SessionResponse with "status": "paused"... }
}
```

**Frontend Use Case:** Triggered by the Pause button in the session player, or automatically when the app moves to the background (app lifecycle event), or when a hand raise is initiated.

---

### POST `/sessions/{session_id}/complete` 🔒

**Purpose:** Mark a session as completed. Records the completion time and final metrics.

**Response (200):**
```json
{
  "success": true,
  "message": "Session completed",
  "data": { ...SessionResponse with "status": "completed"... }
}
```

**Frontend Use Case:** Called automatically when the last segment finishes playing. Triggers the "Session Complete" screen with the completion celebration. Follow up with `POST /content/{id}/notes` to generate downloadable notes.

---

### POST `/sessions/{session_id}/cancel` 🔒

**Purpose:** Cancel a session that will not be continued.

**Response (200):**
```json
{
  "success": true,
  "message": "Session cancelled",
  "data": { ...SessionResponse with "status": "cancelled"... }
}
```

**Frontend Use Case:** The "Cancel Session" option in the session overflow menu (⋮), confirmed with a dialog.

---

### PATCH `/sessions/{session_id}/config` 🔒

**Purpose:** Update session settings mid-session — switch mood, personality, language, study level, or voice on the fly without interrupting or restarting the session.

**Request Body (all fields optional):**
```json
{
  "mood": "exam_prep",
  "model_personality": "motivational",
  "language": "hindi",
  "study_level": "advanced",
  "voice_id": "voice-uuid"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Config updated",
  "data": {
    "session_id": "a1b2c3d4-...",
    "applied": {
      "mood": "exam_prep",
      "model_personality": "motivational",
      "study_level": "advanced",
      "language": "hindi"
    }
  }
}
```

`applied` contains only the fields that were actually sent in the request body (excludes unset fields).

**Frontend Use Case:** The "Session Settings" panel (a slide-up overlay in the player) with dropdowns or sliders for Mood, Personality, and Speed. Apply the change instantly when any setting is adjusted — the AI will adapt for the next segment generated.

---

### GET `/sessions/playlists/{playlist_id}` 🔒

**Purpose:** Get complete details of a playlist (a multi-session series on the same broad topic) including all sessions in their order.

**Response (200):**
```json
{
  "success": true,
  "message": "Playlist retrieved",
  "data": {
    "id": "pl-uuid",
    "user_id": "3d6f8b2a-...",
    "title": "Complete Calculus Course",
    "concept_name": "Calculus",
    "total_sessions": 5,
    "is_complete": false,
    "sessions": [ ...ordered SessionResponse array... ],
    "created_at": "2026-03-17T09:00:00Z"
  }
}
```

**Frontend Use Case:** The "Continue Learning" card on the home dashboard for in-progress playlists. Also used on a dedicated "My Playlists" screen showing overall progress across multi-session learning plans.

---

## 5. Session Playlists

### GET `/sessions/playlists` 🔒

**Purpose:** List all playlists belonging to the current user, paginated.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Items per page (max 100) |

**Response (200):**
```json
{
  "success": true,
  "message": "Playlists retrieved",
  "data": {
    "playlists": [
      {
        "id": "pl-uuid",
        "title": "Complete Calculus Course",
        "concept_name": "Calculus",
        "total_sessions": 5,
        "completed_sessions": 2,
        "is_complete": false,
        "created_at": "2026-03-17T09:00:00Z"
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 20
  }
}
```

| Field | Description |
|---|---|
| `total_sessions` | Total number of sessions planned in the playlist |
| `completed_sessions` | Count of sessions with `status == completed` |
| `is_complete` | `true` when all sessions in the playlist are done |

**Frontend Use Case:** The "My Playlists" screen and the "Continue Learning" section on the home dashboard. Render each playlist as a progress card (`completed_sessions / total_sessions`). Tap to view the individual playlist sessions.

---

## 6. Session Preview & Evaluation

After session creation, the frontend displays the AI-generated `session_evaluation` for the user to review and optionally edit segments, durations, and teaching approaches before starting.

### GET `/sessions/{session_id}/preview` 🔒

**Purpose:** Retrieve the session evaluation data for frontend preview display. Shows the AI's structured plan (segments, teaching strategy, durations) that the user can review before starting the session.

**Response (200):**
```json
{
  "success": true,
  "message": "Session preview retrieved",
  "data": {
    "session_id": "a1b2c3d4-...",
    "concept_name": "Quadratic Equations",
    "description": "Focus on discriminant and nature of roots",
    "user_profession": "college_student",
    "status": "draft",
    "total_duration_seconds": 2700,
    "session_evaluation": {
      "session_overview": {
        "main_concept": "Quadratic Equations",
        "description": "Comprehensive session covering discriminant, nature of roots, and solving techniques",
        "target_audience": "College student, MIT, Mathematics 101, Semester 3",
        "estimated_total_duration_seconds": 2700,
        "difficulty_rating": 3,
        "prerequisites": ["Basic algebra", "Linear equations"]
      },
      "segments": [
        {
          "segment_order": 1,
          "segment_type": "introduction",
          "title": "Introduction to Quadratic Equations",
          "description": "Overview and fundamentals",
          "key_points": ["Definition", "Standard form ax²+bx+c=0"],
          "duration_seconds": 300,
          "teaching_approach": "Start with a warm greeting and broad overview"
        },
        {
          "segment_order": 2,
          "segment_type": "core_teaching",
          "title": "The Discriminant",
          "description": "Deep dive into b²-4ac",
          "key_points": ["b²-4ac formula", "D>0", "D=0", "D<0"],
          "duration_seconds": 900,
          "teaching_approach": "Visual explanation with parabola graphs"
        }
      ],
      "teaching_strategy": {
        "personality_approach": "Very friendly and encouraging",
        "mood_adaptation": "Keep energy high",
        "engagement_techniques": ["Visual aids", "Analogies", "Quiz checks"],
        "language_style": "Clear, conversational English"
      }
    }
  }
}
```

**Frontend Use Case:** The "Session Preview" screen displayed after session creation. Show the segment plan as an editable list — each segment shows title, type, duration, and key points. Allow the user to reorder, add, remove, or edit segments. Show total estimated duration. Provide "Edit & Save" and "Start Session" buttons.

---

### PUT `/sessions/{session_id}/evaluation` 🔒

**Purpose:** Update the session evaluation JSON after the user edits segments in the preview screen. Only works for sessions in `draft` or `ready` status — cannot update after session has started.

**Request Body:**
```json
{
  "session_evaluation": {
    "session_overview": { ...updated overview... },
    "segments": [
      {
        "segment_order": 1,
        "segment_type": "introduction",
        "title": "Updated Introduction",
        "key_points": ["Updated points"],
        "duration_seconds": 400,
        "teaching_approach": "Modified approach"
      }
    ],
    "teaching_strategy": { ...updated strategy... }
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Session evaluation updated",
  "data": {
    "session_id": "a1b2c3d4-...",
    "concept_name": "Quadratic Equations",
    "status": "draft",
    "session_evaluation": { ...updated evaluation... },
    "total_duration_seconds": 2500
  }
}
```

**Response (400 — session already started):**
```json
{
  "success": false,
  "message": "Cannot update evaluation after session has started",
  "data": null
}
```

**Frontend Use Case:** Called when the user taps "Save Changes" on the Session Preview screen after modifying segments. Recalculates total duration from the updated segment durations.

---

## 7. Session End Management

Sessions can end in two ways: **automatically** (when all segments complete or duration is exceeded) or **manually** (via user action). In both cases, the AI tutor generates a personalized goodbye message.

### POST `/sessions/{session_id}/end` 🔒

**Purpose:** Manually end an active session. The AI tutor generates a warm, personality-aligned goodbye message summarizing what was covered and encouraging continued learning. Sets status to `completed`.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Session ended",
  "data": {
    "session_id": "a1b2c3d4-...",
    "status": "completed",
    "goodbye_message": "[warm] Great job today! We covered a lot about Quadratic Equations. [encouraging] You've made real progress understanding the discriminant. Keep practicing those problems and you'll master it in no time! See you next time!",
    "completion_percentage": 65.0
  }
}
```

**Response (400 — already ended):**
```json
{
  "success": false,
  "message": "Session already ended",
  "data": null
}
```

**Frontend Use Case:** Triggered by the "End Session" button in the player UI. After receiving the response, display the goodbye message with the tutor's avatar/animation. Show the completion percentage and offer "Generate Notes" and "Return to Home" buttons.

### Auto-End Behavior

Sessions auto-end when:
1. **All segments completed** — After the last segment's SSE stream finishes, the stream response includes an `event: session_end` SSE event with the goodbye message.
2. **Duration exceeded** — If the elapsed time exceeds the total estimated duration, auto-end triggers after the current segment completes.

The auto-end check happens automatically during SSE streaming (see [Real-Time Teaching Stream](#8-real-time-teaching-stream-sse)). No separate API call is needed.

---

## 8. Lazy Segment Generation

Sessions are created with a full segment plan from the evaluation, but only **segment 1** has its `content_script` pre-generated. All subsequent segments have `content_script: null` to reduce initial session creation time. Call this endpoint to generate content for each segment **just before it is needed**.

### POST `/sessions/{session_id}/segments/{segment_order}/generate` 🔒

**Purpose:** Generate the full `content_script`, `whiteboard_cues`, and `animation_cues` for a specific segment on demand. The AI uses the previous segment's content as context to ensure continuity in teaching. If the segment already has a script (previously generated), returns the cached version instantly without re-calling the AI.

**URL Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `session_id` | UUID | The session ID |
| `segment_order` | int | 1-based position of the segment (e.g., `2`, `3`, `4`...) |

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Segment 2 content generated",
  "data": {
    "id": "seg-uuid-2",
    "session_id": "a1b2c3d4-...",
    "segment_order": 2,
    "segment_type": "explanation",
    "title": "Understanding the Discriminant",
    "content_script": "Alright! So now that we know what a quadratic equation looks like [PAUSE: 0.5s] let's talk about something called the *discriminant*. [EMOTION: curious] Here's the formula: [WHITEBOARD: action=formula, content=D = b²-4ac] ...",
    "key_points": ["b²-4ac", "D>0: two distinct real roots", "D=0: one repeated root", "D<0: no real roots"],
    "teaching_notes": "Use visual of parabola touching/crossing x-axis",
    "duration_seconds": 600,
    "whiteboard_cues": {
      "type": "formula",
      "content": "D = b² - 4ac"
    },
    "animation_cues": {
      "type": "graph_plot",
      "data": { "function": "x^2-4x+3", "highlight_roots": true }
    },
    "status": "pending",
    "created_at": "2026-03-17T10:05:00Z"
  }
}
```

**Frontend Use Case:** Call this endpoint **while the current segment is still playing** — ideally when the current segment is ~70–80% complete. This pre-loads the next segment in the background so it is seamlessly ready when the transition happens. Never wait until the current segment finishes before requesting the next one, as AI generation takes a few seconds.

---

## 9. Real-Time Teaching Stream (SSE)

The frontend connects to a **Server-Sent Events** endpoint to stream each segment's pre-generated teaching script as a sequence of typed JSON events. The backend **never calls the AI model during streaming** — it reads the `content_script` saved during session start / lazy generation and parses it into structured events.

### GET `/sessions/{session_id}/segments/{segment_order}/stream`

**Authentication:** Via `Authorization: Bearer <token>` header **OR** `?token=<jwt>` query param. The query-param form is required for browsers using `EventSource` which cannot set custom headers.

**URL Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `session_id` | UUID | The session ID |
| `segment_order` | int | 1-based position of the segment to stream |

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `token` | string | — | JWT auth token (for `EventSource` clients that cannot set headers) |
| `from_chunk` | int | `0` | Resume stream from this chunk number. `0` = stream from the beginning. Use `lastChunk + 1` when reconnecting after a pause. |

**Response:** `Content-Type: text/event-stream`

All events use a single `data:` line — no `event:` prefix. The `type` field inside the JSON payload identifies the event kind. **Every event includes a `chunk` integer field** — the frontend stores this number so it can resume exactly where it left off.

```
data: {"type": "segment_start", "segment_order": 1, "title": "Introduction", "duration_seconds": 180, "total_segments": 6, "chunk": 0}

data: {"type": "emotion", "value": "warm", "chunk": 1}

data: {"type": "text", "value": "Hey there! Welcome to organic chemistry.", "chunk": 2}

data: {"type": "pause", "duration": 400, "chunk": 3}

data: {"type": "text", "value": "Carbon is the backbone of all living things.", "chunk": 4}

data: {"type": "whiteboard", "action": "draw", "content_type": "diagram", "description": "Show a simple diagram of carbon-based molecules", "id": "wb_1_1", "chunk": 5}

data: {"type": "text", "value": "Notice how carbon bonds with four hydrogen atoms.", "chunk": 6}

data: {"type": "segment_end", "segment_order": 1, "chunk": 47}
```

For the final segment only, a `session_end` event follows `segment_end`:

```
data: {"type": "session_end", "session_id": "ed970bb9-...", "chunk": 48}
```

On error:

```
data: {"type": "error", "code": "not_found", "message": "Segment not found"}
data: {"type": "error", "code": "bad_request", "message": "Session is not in progress"}
data: {"type": "error", "code": "server_error", "message": "An unexpected error occurred"}
```

**Complete SSE Event Type Reference:**

| `type` | Fields | Frontend action |
|---|---|---|
| `segment_start` | `segment_order`, `title`, `duration_seconds`, `total_segments`, `chunk` (always 0) | Show segment title, initialise progress bar. **Always emitted even on resume.** |
| `emotion` | `value` (`warm`/`curious`/`calm`/`excited`/`serious`/`friendly`), `chunk` | Update voice style — frontend maps to Web Speech API pitch + rate delta |
| `text` | `value`, `chunk` | Push sentence to TTS queue, append to transcript |
| `pause` | `duration` (ms int), `chunk` | Insert delay between TTS sentence calls |
| `whiteboard` | `action`, `content_type`, `description`, `id`, `chunk` | Draw/update/clear canvas |
| `segment_end` | `segment_order`, `chunk` | Drain TTS queue → open next segment stream |
| `session_end` | `session_id`, `chunk` | Drain TTS queue → POST complete → show completion UI |
| `error` | `code`, `message` | Show error toast, stop playback |

**Response Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**Pause & Resume with chunk tracking:**

Every SSE event carries a `chunk` field (integer, starting at 0 for `segment_start`). The frontend stores the last received chunk to resume exactly where it left off:

```javascript
let lastChunk = 0;

es.onmessage = (e) => {
  const event = JSON.parse(e.data);
  lastChunk = event.chunk ?? lastChunk;  // always track
  // ... handle event ...
};

// On pause/disconnect
function pauseStream() {
  es.close();
  localStorage.setItem(`chunk_${sessionId}_${segmentOrder}`, lastChunk);
}

// On resume
function resumeStream() {
  const fromChunk = Number(localStorage.getItem(`chunk_${sessionId}_${segmentOrder}`)) || 0;
  const url = `/api/v1/sessions/${sessionId}/segments/${segmentOrder}/stream`
            + `?token=${jwt}&from_chunk=${fromChunk + 1}`;
  const es = new EventSource(url);
}
```

> `segment_start` (chunk 0) is **always emitted** regardless of `from_chunk`. This signals a successful reconnect and provides segment metadata.

**Segment switching flow (frontend responsibility):**

1. Receive `segment_end` → close current `EventSource`
2. Wait for TTS audio queue to fully drain
3. Open new `EventSource` for `segment_order + 1`

**Session end flow:**

1. Receive `session_end` → close `EventSource`
2. Wait for TTS audio queue to drain
3. Call `POST /sessions/{id}/end`
4. Show completion screen

**Example Frontend Code (JavaScript):**
```javascript
const url = `/api/v1/sessions/${sessionId}/segments/${segmentOrder}/stream?token=${jwt}`;
const es = new EventSource(url);
let currentEmotion = 'neutral';
let lastChunk = 0;

es.onmessage = (e) => {
  const event = JSON.parse(e.data);
  lastChunk = event.chunk ?? lastChunk;
  switch (event.type) {
    case 'segment_start':
      updateProgressBar(event.segment_order, event.total_segments);
      break;
    case 'emotion':
      currentEmotion = event.value;
      break;
    case 'text':
      appendToTranscript(event.value);
      ttsQueue.push({ type: 'text', text: event.value, emotion: currentEmotion });
      break;
    case 'pause':
      ttsQueue.push({ type: 'pause', ms: event.duration });
      break;
    case 'whiteboard':
      renderWhiteboard(event);
      break;
    case 'segment_end':
      es.close();
      ttsQueue.onEmpty = () => openNextSegment(event.segment_order);
      break;
    case 'session_end':
      es.close();
      ttsQueue.onEmpty = () => completeSession(event.session_id);
      break;
    case 'error':
      showErrorToast(event.message);
      es.close();
      break;
  }
};
```

See [SESSION_STREAMING_README.md](SESSION_STREAMING_README.md) for the complete Web Speech API TTS integration guide, emotion → voice settings mapping, whiteboard rendering (KaTeX, animations), and buffer-replay pause/resume documentation.

---

## 10. Interactions — Doubts & Hand Raise

### POST `/interactions/hand-raise` 🔒

**Purpose:** Signal that the student wants to pause teaching and ask a question. Returns a natural, personality-aligned acknowledgement phrase from the tutor. The session should be paused on the frontend after calling this.

**Request Body:**
```json
{
  "session_id": "a1b2c3d4-...",
  "timestamp_in_session_seconds": 240
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Hand raised acknowledged",
  "data": {
    "id": "interaction-uuid",
    "session_id": "a1b2c3d4-...",
    "interaction_type": "hand_raise",
    "ai_response": "Oh! I can see you have a question! Take your time — I'm all ears.",
    "timestamp_in_session_seconds": 240
  }
}
```

**Frontend Use Case:** The prominent "Raise Hand" / "Stop" button in the session player UI (typically a large hand icon). Tapping it pauses audio playback, calls this endpoint, and displays the `ai_response` text (play it via TTS). Then reveal the "Tell me your doubt" input panel.

---

### POST `/interactions/doubts` 🔒

**Purpose:** Submit a text or image-based doubt to the AI tutor for resolution. Supports multipart form so the student can photograph a handwritten question, textbook page, or whiteboard problem — the image is processed via OCR to extract text.

**Request (multipart/form-data):**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | UUID | ✅ | The active session ID |
| `doubt_text` | string | ❌ | Text description of the doubt |
| `timestamp_in_session_seconds` | int | ❌ | When in the session the doubt arose |
| `doubt_image` | file | ❌ | JPG or PNG photo (processed by OCR to extract question text) |

**Response (200):**
```json
{
  "success": true,
  "message": "Doubt submitted",
  "data": {
    "id": "doubt-uuid",
    "session_id": "a1b2c3d4-...",
    "doubt_text": "What does it mean physically when the discriminant is negative?",
    "ai_response": "Great question! When D < 0, the parabola sits entirely above or below the x-axis — it never crosses it. Physically, this means the equation has no real solution...",
    "resolution_method": "ai_explanation",
    "is_resolved": false,
    "timestamp_in_session_seconds": 245
  }
}
```

**Frontend Use Case:** The doubt submission panel that appears after a hand raise — a text input and optional camera button. Submit on "Ask" tap. Display the `ai_response` in a speech bubble or chat-style layout, play it via TTS. After the student is satisfied, show a "Resolved — Continue" button that calls `/doubts/resolve`.

---

### GET `/interactions/doubts/{session_id}` 🔒

**Purpose:** Retrieve all doubts submitted during a session, including the AI's answers.

**Response (200):**
```json
{
  "success": true,
  "message": "Doubts retrieved",
  "data": [
    {
      "id": "doubt-uuid",
      "doubt_text": "What is the discriminant?",
      "ai_response": "The discriminant is b²-4ac. It tells you how many real roots the equation has...",
      "is_resolved": true,
      "timestamp_in_session_seconds": 245
    }
  ]
}
```

**Frontend Use Case:** The "Doubts" tab on the session review / summary screen after the session ends. Students can revisit all their questions and the AI's answers as a learning resource.

---

### POST `/interactions/doubts/resolve` 🔒

**Purpose:** Mark a specific doubt as resolved and signal the tutor to resume teaching.

**Request Body:**
```json
{
  "doubt_id": "doubt-uuid",
  "resolution_method": "ai_explanation",
  "user_message": "Got it, thanks!"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Doubt resolved",
  "data": { ...DoubtResponse with "is_resolved": true... }
}
```

**Frontend Use Case:** The "Resolved — Continue Teaching" button shown below the AI's doubt response. After the student indicates they understood, call this endpoint and resume audio/session playback.

---

### POST `/interactions/doubts/{session_id}/stream-answer` 🔒

**Purpose:** Stream an AI-generated answer to a live doubt in real time, with the active segment's content as context. Events are emitted sentence-by-sentence so the frontend can start TTS immediately without waiting for the full response.

**Authentication:** `Authorization: Bearer <jwt>` header **or** `?token=<jwt>` query param. Since `EventSource` only supports `GET`, use `fetch()` with a `ReadableStream` reader for this `POST` endpoint.

**Request Body:**
```json
{
  "query_text": "Why does carbon form exactly 4 bonds?",
  "segment_order": 1
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query_text` | string | ✅ | Student's question (3–2000 chars) |
| `segment_order` | int | ❌ | Segment providing context. Defaults to active `IN_PROGRESS` segment. |

**Response:** `Content-Type: text/event-stream`

```
data: {"type": "doubt_start", "query": "Why does carbon form exactly 4 bonds?"}

data: {"type": "text", "value": "Great question!", "chunk": 1}

data: {"type": "text", "value": "Carbon has 4 valence electrons, meaning it needs 4 more to complete its outer shell.", "chunk": 2}

data: {"type": "text", "value": "This is why forming 4 covalent bonds gives the most stable configuration.", "chunk": 3}

data: {"type": "doubt_end", "chunk": 4}
```

On error:
```
data: {"type": "error", "code": "stream_error", "message": "Answer stream failed"}
```

**SSE Event Reference:**

| `type` | Fields | Description |
|---|---|---|
| `doubt_start` | `query` | Confirms streaming started. Echo of the student's question. |
| `text` | `value`, `chunk` | One complete sentence of the answer. Queue for TTS. |
| `doubt_end` | `chunk` | Streaming complete. |
| `error` | `code`, `message` | Something went wrong. |

**Pulse effect:** On stream completion or client disconnect, the student's pulse is auto-incremented by **+4** (`live_doubt_resolved`).

**Frontend integration (using fetch + ReadableStream):**
```javascript
const response = await fetch(
  `/api/v1/interactions/doubts/${sessionId}/stream-answer`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwt}`,
    },
    body: JSON.stringify({ query_text: question, segment_order: currentSegment }),
  }
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  for (const line of text.split('\n')) {
    if (!line.startsWith('data: ')) continue;
    const event = JSON.parse(line.slice(6));
    if (event.type === 'text') ttsQueue.push(event.value);
    if (event.type === 'doubt_end') closeDoubtPanel();
  }
}
```

---

The pulse meter is an **activity-based engagement tracker**. Various user activities during a session automatically increase or decrease the pulse percentage. The frontend can also make direct adjustments via the adjust endpoint.

**Activity Deltas (automatic):**

| Activity | Delta | Trigger |
|---|---|---|
| `doubt_raised` | +8 | Student raises a doubt |
| `chat_message` | +5 | Student sends a chat message |
| `hand_raise` | +10 | Student raises hand |
| `mcq_correct` | +12 | Student answers MCQ correctly |
| `mcq_incorrect` | -3 | Student answers MCQ incorrectly |
| `go_ahead` | +3 | Student clicks "Go Ahead" / continue |
| `config_change` | +2 | Student changes session config mid-session |
| `live_doubt_resolved` | +4 | Student streams a live doubt answer |
| `inactivity` | -10 | Frontend detects prolonged inactivity |

Pulse percentage is always clamped between `0.0` and `100.0`. Default starting value: `50.0`.

---

### POST `/interactions/pulse/{session_id}/record` 🔒

**Purpose:** Record a self-reported focus level for the session. The backend logs the reading, updates the pulse meter, and returns the updated attention status.

**Request Body:**
```json
{
  "focus_level": 75.0,
  "notes": "Feeling focused but slightly tired",
  "timestamp_in_session_seconds": 300
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `focus_level` | float | ✅ | Self-reported focus level 0–100 |
| `notes` | string | ❌ | Optional free-text note about current focus state |
| `timestamp_in_session_seconds` | int | ❌ | Position in session when this reading was taken |

**Response (200):**
```json
{
  "success": true,
  "message": "Pulse recorded",
  "data": {
    "session_id": "a1b2c3d4-...",
    "current_pulse": 75.0,
    "average_pulse": 68.5,
    "pulse_percentage": 75.0,
    "recommendation": "Pace is good. Keep going.",
    "should_downgrade_level": false,
    "should_change_personality": false
  }
}
```

**Frontend Use Case:** Called by the attention tracking module when the student manually adjusts a focus slider, or by a periodic check-in prompt ("How focused are you right now?"). When `should_downgrade_level: true`, optionally prompt the user if they want to reduce the study level for the next segment.

---

### POST `/interactions/pulse/{session_id}/adjust` 🔒

**Purpose:** Frontend-triggered direct pulse adjustment. Use this for custom UI interactions that should affect engagement (e.g., a thumbs-up button, a "pay attention" nudge, or periodic inactivity penalties).

**Request Body:**
```json
{
  "adjustment": 5.0,
  "reason": "thumbs_up_button",
  "timestamp_in_session_seconds": 300
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `adjustment` | float | ✅ | Value between `-50.0` and `+50.0`. Positive = boost, negative = penalty. |
| `reason` | string | ❌ | Short label for analytics (e.g., `"inactivity_penalty"`, `"manual_boost"`) |
| `timestamp_in_session_seconds` | int | ❌ | Position in session when this adjustment occurred |

**Response (200):**
```json
{
  "success": true,
  "message": "Pulse adjusted",
  "data": {
    "session_id": "a1b2c3d4-...",
    "pulse_percentage": 55.0,
    "current_pulse": 55.0,
    "average_pulse": 52.0
  }
}
```

**Frontend Use Case:** Wire this to any custom engagement UI elements — an inactivity timer that sends `-10` after 2 minutes of no interaction, a "Still here!" button that sends `+5`, or gamification elements in the session player.

---

### POST `/interactions/pulse/{session_id}/activity` 🔒
<!-- (unchanged) -->

**Purpose:** Record a named activity event. The backend automatically applies the corresponding delta from the activity deltas table above and returns the updated pulse percentage.

**Request Body:**
```json
{
  "activity_type": "hand_raise",
  "timestamp_in_session_seconds": 180
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `activity_type` | string | ✅ | One of: `doubt_raised`, `chat_message`, `hand_raise`, `mcq_correct`, `mcq_incorrect`, `go_ahead`, `config_change`, `inactivity` |
| `timestamp_in_session_seconds` | int | ❌ | Position in session when the activity occurred |

**Response (200):**
```json
{
  "success": true,
  "message": "Activity recorded",
  "data": {
    "session_id": "a1b2c3d4-...",
    "activity_type": "hand_raise",
    "delta_applied": 10.0,
    "pulse_percentage": 60.0
  }
}
```

**Frontend Use Case:** Called automatically by interaction handlers (doubt, chat, hand raise, MCQ). Can also be called directly for events the frontend tracks independently (e.g., `inactivity` when the user hasn't touched the screen for a while). The response gives the updated pulse to refresh the pulse meter widget.

---

### GET `/interactions/pulse/{session_id}` 🔒

**Purpose:** Get the current pulse/engagement summary and rolling average for the session.

**Response (200):**
```json
{
  "success": true,
  "message": "Pulse retrieved",
  "data": {
    "session_id": "a1b2c3d4-...",
    "current_status": "moderate_attention",
    "average_score": 68.5,
    "total_readings": 12,
    "recommendation": "Pace is good. Keep going.",
    "pulse_percentage": 55.0,
    "recent_metrics": [ ...last 5 PulseMetric objects... ]
  }
}
```

**Frontend Use Case:** The pulse/engagement indicator widget in the session player HUD. Shows a circular gauge or bar from 0–100% with color coding (green > 70%, yellow 40–70%, red < 40%). Refresh this periodically or after any interaction to keep the pulse meter widget up to date.

---

## 12. Interactions — MCQ

### POST `/interactions/mcq/{session_id}/generate` 🔒

**Purpose:** Generate 3–5 multiple-choice comprehension questions on the current topic as an attention pulse check.

**Query Parameter:** `topic` (string) — the concept the questions should cover.

**Example:** `POST /interactions/mcq/a1b2c3d4.../generate?topic=Discriminant`

**Response (200):**
```json
{
  "success": true,
  "message": "MCQs generated",
  "data": {
    "questions": [
      {
        "id": "q-uuid-1",
        "question": "If D = b² - 4ac < 0, the quadratic equation has:",
        "options": [
          "A. Two real roots",
          "B. One real root",
          "C. No real roots",
          "D. Infinite roots"
        ],
        "correct_answer": "C",
        "explanation": "A negative discriminant indicates the square root would be imaginary, so no real roots exist."
      }
    ]
  }
}
```

**Frontend Use Case:** Triggered automatically when `should_trigger_mcq: true` in a pulse record response, or when pulse percentage drops below 40%. Show a full-screen or overlay MCQ quiz panel. Pause the session timer while the quiz is active. Display one question at a time with option buttons.

---

### POST `/interactions/mcq/submit` 🔒

**Purpose:** Submit the student's answer to an MCQ question. Returns correctness, explanation, and (for correct answers) a celebration message. Also automatically adjusts the pulse meter (`mcq_correct: +12`, `mcq_incorrect: -3`).

**Request Body:**
```json
{
  "session_id": "a1b2c3d4-...",
  "question_id": "q-uuid-1",
  "user_answer": "C"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "MCQ answer submitted",
  "data": {
    "question_id": "q-uuid-1",
    "user_answer": "C",
    "correct_answer": "C",
    "is_correct": true,
    "explanation": "Correct! A negative discriminant (D < 0) means no real roots exist.",
    "celebration_message": "Excellent! You really understood that concept! 🎉",
    "pulse_percentage": 72.0
  }
}
```

**Frontend Use Case:** Called when the student taps an answer option. If `is_correct: true`, show a celebration animation and the `celebration_message`. If `is_correct: false`, highlight the wrong answer in red, show the correct answer in green, and display the `explanation` to reinforce understanding before resuming the session. Update the pulse meter widget with the new `pulse_percentage`.

---

## 13. Interactions — Chat

### POST `/interactions/chat` 🔒

**Purpose:** Send a free-form text message to the AI tutor during a session. The AI responds in the context of the current lesson using the session's personality and study level settings.

**Request Body:**
```json
{
  "session_id": "a1b2c3d4-...",
  "message": "Can you give me a real-world example of this?",
  "timestamp_in_session_seconds": 520
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Chat response generated",
  "data": {
    "id": "interaction-uuid",
    "session_id": "a1b2c3d4-...",
    "interaction_type": "chat",
    "user_message": "Can you give me a real-world example of this?",
    "ai_response": "Of course! Think about throwing a ball straight up in the air — its height over time follows a quadratic equation h(t) = -4.9t² + v₀t + h₀. The roots tell you exactly when the ball hits the ground!",
    "timestamp_in_session_seconds": 520
  }
}
```

**Frontend Use Case:** The collapsible chat input bar at the bottom of the session player. Useful for quick clarifying questions without interrupting the full hand-raise / doubt flow. Suitable for conversational exchanges ("Can you slow down?", "What's the formula again?").

---

## 14. Content & Visuals

### POST `/content/{session_id}/generate` 🔒

**Purpose:** Trigger AI generation of animation data and structured whiteboard content for the full session. Analyzes all segments and creates visual events (graph plots, diagrams, formula boards, flowcharts, etc.) tied to segment positions.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Content generated",
  "data": {
    "animations": [
      {
        "id": "anim-uuid",
        "animation_type": "graph_plot",
        "animation_data": {
          "function": "x^2 - 5x + 6",
          "x_range": [-1, 6],
          "highlight_roots": true,
          "label": "y = x² - 5x + 6"
        },
        "trigger_text": "Let's visualize this parabola",
        "segment_order": 2
      }
    ],
    "whiteboards": [
      {
        "id": "wb-uuid",
        "drawing_instructions": {
          "type": "formula",
          "content": "x = (-b ± √(b²-4ac)) / 2a",
          "position": "center"
        },
        "segment_order": 3
      }
    ],
    "timeline": [
      { "time_seconds": 30, "type": "animation", "description": "Graph: parabola for x²-5x+6" },
      { "time_seconds": 90, "type": "whiteboard", "description": "Quadratic formula" }
    ]
  }
}
```

**Supported animation types:** `graph_plot`, `diagram`, `flowchart`, `timeline_chart`, `comparison_table`, `equation_step`, `visualization_3d`, `mind_map`, `bar_chart`, `pie_chart`, `scatter_plot`

**Frontend Use Case:** Called once after session creation, just before the player begins. The stored `animations` and `whiteboards` are used to sync visuals with the AI tutor's speech through `[ANIMATION:]` and `[WHITEBOARD:]` markers embedded in `content_script`.

---

### GET `/content/{session_id}` 🔒

**Purpose:** Retrieve all previously generated visual content, including animations, whiteboard data, and notes (if generated) for a session.

**Response (200):**
```json
{
  "success": true,
  "message": "Content retrieved",
  "data": {
    "animations": [ ...AnimationData array... ],
    "whiteboards": [ ...WhiteboardData array... ],
    "notes": null,
    "timeline": [ ...timeline event array... ]
  }
}
```

**Frontend Use Case:** When resuming a session — reload the content state to restore the visual timeline without regenerating it. Also used on the session review / replay screen.

---

### POST `/content/{session_id}/notes` 🔒

**Purpose:** AI-generate structured session notes — a markdown summary, key points list, important formulas, and a full dialogue transcript. This is a one-time generation; subsequent calls return the cached version.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Notes generated",
  "data": {
    "id": "notes-uuid",
    "session_id": "a1b2c3d4-...",
    "content_markdown": "# Quadratic Equations\n\n## What is a Quadratic Equation?\n\nA quadratic equation is a polynomial of degree 2 in the standard form **ax² + bx + c = 0**...\n\n## The Discriminant\n\nD = b² - 4ac determines the nature of roots:\n- D > 0 → Two distinct real roots\n- D = 0 → One repeated real root\n- D < 0 → No real roots (complex)",
    "key_points": [
      "Standard form: ax² + bx + c = 0",
      "Discriminant: D = b² - 4ac",
      "D > 0: two real roots, D = 0: one root, D < 0: complex roots",
      "Quadratic formula: x = (-b ± √D) / 2a"
    ],
    "formulas": [
      "D = b² - 4ac",
      "x = (-b ± √(b²-4ac)) / 2a"
    ],
    "transcript": "Hey! So today we are going to dive into quadratic equations..."
  }
}
```

**Frontend Use Case:** The "Generate Notes" button on the session completion screen. Render `content_markdown` in a rich text / markdown viewer. Display `key_points` as highlighted cards and `formulas` in a formula grid rendered with KaTeX. Offer a "Download PDF" button that calls `GET /content/{id}/notes/pdf`.

---

### GET `/content/{session_id}/notes/pdf` 🔒

**Purpose:** Download the session notes as a formatted PDF file, generated from the notes content. If notes have not yet been generated, generates them first.

**Response:** Binary PDF (`application/pdf`), attachment header: `Content-Disposition: attachment; filename=session_notes_{session_id}.pdf`

**Frontend Use Case:** The "Download PDF" button on the Notes screen. Trigger a file download (browser) or a save-to-device dialog (mobile). The PDF includes the session title, key points, formulas, and the full markdown content.

---

## 15. Whiteboard Timeline

### GET `/content/{session_id}/whiteboard-timeline` 🔒

**Purpose:** Get a complete, per-segment, synchronized whiteboard instruction timeline for the session. Each entry contains typed drawing instructions (text labels, formulas, diagrams, code blocks, tables, or clear commands) parsed from the `[WHITEBOARD:]` markers embedded in each segment's `content_script`. This is a zero-cost, zero-AI-call endpoint — it parses existing content.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Whiteboard timeline generated",
  "data": [
    {
      "segment_order": 1,
      "segment_title": "What are Quadratic Equations?",
      "events": [
        {
          "type": "text",
          "content": "Quadratic Equation",
          "position": "top-center",
          "style": "heading"
        },
        {
          "type": "formula",
          "content": "ax² + bx + c = 0",
          "position": "center",
          "style": "large"
        }
      ]
    },
    {
      "segment_order": 2,
      "segment_title": "Understanding the Discriminant",
      "events": [
        {
          "type": "formula",
          "content": "D = b² - 4ac",
          "position": "top-left",
          "style": "normal"
        },
        {
          "type": "diagram",
          "nodes": [
            { "id": "D", "label": "Discriminant" },
            { "id": "pos", "label": "D > 0: Two real roots" },
            { "id": "zero", "label": "D = 0: One root" },
            { "id": "neg", "label": "D < 0: No real roots" }
          ],
          "edges": [
            { "from": "D", "to": "pos" },
            { "from": "D", "to": "zero" },
            { "from": "D", "to": "neg" }
          ]
        }
      ]
    }
  ]
}
```

**Supported whiteboard instruction types:**

| Type | Render As | Key Fields |
|---|---|---|
| `text` | Text label or heading on canvas | `content`, `position`, `style` (`heading`/`normal`/`small`) |
| `formula` | Mathematical formula — render with KaTeX | `content` (LaTeX string), `position` |
| `diagram` | Node-edge flowchart/graph | `nodes[]` (id, label), `edges[]` (from, to) |
| `step` | Numbered process step | `step_number`, `description` |
| `code_block` | Code snippet with syntax highlight | `language`, `code` |
| `table` | Data table | `headers[]`, `rows[][]` |
| `shape` | Geometric shape | `shape_type`, `label` |
| `clear` | Clear the canvas entirely | — |

**Frontend Use Case:** Fetch this once when the session player initializes (alongside `GET /content/{id}`). Use it to drive a dedicated whiteboard/canvas panel that renders alongside the AI tutor's audio. On each segment transition, load the `events` for that `segment_order` and draw/animate them on the canvas sequentially as the tutor's speech progresses. Formulas should be rendered using KaTeX, diagrams using a graph layout library (e.g., Cytoscape.js, d3-force), and code blocks with a syntax highlighter.

---

## 16. Curriculum

The curriculum hierarchy is: **Board → Subject → Chapter → Topic → Question Bank**.

- **School boards** (CBSE, ICSE, State boards): `board_type: "school"`, subjects linked to class/grade
- **College/University boards**: `board_type: "university"`, subjects linked to degree + semester
- **Competitive exams** (JEE, NEET, UPSC): `board_type: "competitive_exam"`

### GET `/curriculum/boards`

**Purpose:** List all educational boards/universities. No authentication required — publicly accessible.

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `board_type` | string | Filter: `school`, `university`, or `competitive_exam` |

**Response (200):**
```json
{
  "success": true,
  "message": "Boards retrieved",
  "data": [
    {
      "id": "board-uuid-1",
      "name": "CBSE",
      "description": "Central Board of Secondary Education",
      "country": "India",
      "board_type": "school",
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "board-uuid-2",
      "name": "University of Delhi",
      "description": "DU undergraduate curriculum",
      "country": "India",
      "board_type": "university",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** The board selection step in the onboarding flow ("Which board/university are you from?"). Display boards grouped by `board_type` — school students see school boards, college students see universities.

---

### GET `/curriculum/boards/{board_id}`

**Purpose:** Get full details of a board, including its list of subjects.

**Response (200):** `BoardDetailResponse` — `BoardResponse` + `subjects: []` array.

**Frontend Use Case:** Tapping a board in the selection list to preview its subjects before confirming the selection.

---

### POST `/curriculum/boards` 🔒

**Purpose:** Create a new educational board or university entry.

**Request Body:**
```json
{
  "name": "ICSE",
  "description": "Indian Certificate of Secondary Education",
  "country": "India",
  "board_type": "school"
}
```

`board_type` options: `school`, `university`, `competitive_exam`

**Response (201):**
```json
{
  "success": true,
  "message": "Board created",
  "data": {
    "id": "new-board-uuid",
    "name": "ICSE",
    "description": "Indian Certificate of Secondary Education",
    "country": "India",
    "board_type": "school",
    "created_at": "2026-03-17T10:00:00Z"
  }
}
```

**Frontend Use Case:** Admin panel — "Add New Board" form. Also used during data seeding for initial curriculum setup.

---

### GET `/curriculum/boards/{board_id}/subjects`

**Purpose:** List subjects under a board, with optional filtering by grade/class and semester.

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `grade` | string | For school: `"Class 10"`. For college: `"B.Tech CSE"` |
| `semester` | string | College only — semester number: `"3"`, `"5"`, etc. |

**Response (200):**
```json
{
  "success": true,
  "message": "Subjects retrieved",
  "data": [
    {
      "id": "sub-uuid",
      "board_id": "board-uuid",
      "name": "Mathematics",
      "grade": "Class 10",
      "semester": null,
      "description": "Algebra, Geometry, Trigonometry",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** After the user selects a board, show the subjects filtered by their class or semester. For school students, filter by `grade` (e.g., "Class 10"). For college students, filter by `semester` (e.g., "3rd semester subjects").

---

### POST `/curriculum/subjects` 🔒

**Purpose:** Create a new subject under a board.

**Request Body:**
```json
{
  "board_id": "board-uuid",
  "name": "Physics",
  "grade": "Class 11",
  "semester": null,
  "description": "Mechanics, Optics, Thermodynamics"
}
```

For a college subject: `"grade": "B.Tech CSE"`, `"semester": "3"`.

**Response (201):** `SubjectResponse` object.

**Frontend Use Case:** Admin panel — "Add Subject" form for a selected board.

---

### GET `/curriculum/subjects/{subject_id}/chapters`

**Purpose:** List all chapters within a subject.

**Response (200):**
```json
{
  "success": true,
  "message": "Chapters retrieved",
  "data": [
    {
      "id": "chap-uuid",
      "subject_id": "sub-uuid",
      "name": "Quadratic Equations",
      "chapter_number": 4,
      "description": "Roots, discriminant, factorization methods",
      "estimated_hours": 3,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** The chapter selection screen after the user picks a subject. Shown as a numbered list with chapter name and estimated time. Used to pre-fill `chapter_id` when creating a session from the curriculum path.

---

### POST `/curriculum/chapters` 🔒

**Purpose:** Create a new chapter under a subject.

**Request Body:**
```json
{
  "subject_id": "sub-uuid",
  "name": "Quadratic Equations",
  "chapter_number": 4,
  "description": "Roots, discriminant, factorization",
  "estimated_hours": 3
}
```

**Response (201):** `ChapterResponse` object.

**Frontend Use Case:** Admin panel — "Add Chapter" form.

---

### GET `/curriculum/chapters/{chapter_id}/topics`

**Purpose:** List all topics within a chapter.

**Response (200):**
```json
{
  "success": true,
  "message": "Topics retrieved",
  "data": [
    {
      "id": "topic-uuid",
      "chapter_id": "chap-uuid",
      "name": "Discriminant and Nature of Roots",
      "topic_number": 2,
      "description": "Analyzing b²-4ac",
      "key_concepts": ["discriminant", "real roots", "complex roots", "repeated root"],
      "estimated_minutes": 40,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** After selecting a chapter, show topic cards. When the user selects a topic, auto-populate the session creation form: `concept_name` ← topic name, `topic_id` ← topic UUID, and optionally surface `key_concepts` as suggested focus areas.

---

### POST `/curriculum/topics` 🔒

**Purpose:** Create a new topic under a chapter.

**Request Body:**
```json
{
  "chapter_id": "chap-uuid",
  "name": "Completing the Square",
  "topic_number": 3,
  "description": "Solving quadratics by completing the square",
  "key_concepts": ["perfect square trinomial", "vertex form", "completing the square method"],
  "estimated_minutes": 35
}
```

**Response (201):** `TopicResponse` object.

**Frontend Use Case:** Admin panel — "Add Topic" form.

---

### GET `/curriculum/question-banks` 🔒

**Purpose:** List question banks. Optionally filter to a specific topic.

**Query Parameters:** `topic_id` (UUID, optional)

**Response (200):**
```json
{
  "success": true,
  "message": "Question banks retrieved",
  "data": [
    {
      "id": "qb-uuid",
      "user_id": null,
      "topic_id": "topic-uuid",
      "title": "Quadratic Equations — Practice Set",
      "is_predefined": true,
      "questions": [
        {
          "question": "Solve x² - 5x + 6 = 0",
          "answer": "x = 2 or x = 3",
          "difficulty": "easy",
          "type": "solve"
        }
      ],
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** The "Practice" section for a topic. Used when the user creates a session with `entire_session_type: "practice_problems"` to optionally provide a question bank for the AI to draw from.

---

### POST `/curriculum/question-banks` 🔒

**Purpose:** Create a custom question bank for a topic.

**Request Body:**
```json
{
  "topic_id": "topic-uuid",
  "title": "My Algebra Practice Set",
  "questions": [
    {
      "question": "Find the roots of x² + 2x - 3 = 0",
      "answer": "x = 1 or x = -3",
      "difficulty": "medium",
      "type": "solve"
    }
  ]
}
```

**Response (201):** `QuestionBankResponse` object.

**Frontend Use Case:** A "Create Question Bank" builder screen where students or teachers manually add questions and answers.

---

## 17. Voices

### GET `/voices`

**Purpose:** List all available AI tutor voice profiles with their details. No authentication required.

**Response (200):**
```json
{
  "success": true,
  "message": "Voices retrieved",
  "data": [
    {
      "id": "voice-uuid",
      "name": "Priya",
      "language": "English",
      "gender": "female",
      "accent": "Indian",
      "description": "Warm, encouraging tone. Great for school and college students.",
      "preview_url": "https://cdn.example.com/previews/priya.mp3",
      "tutor_name": "Priya",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Frontend Use Case:** The voice selection screen during session creation ("Choose your tutor"). Render each voice as a card with name, gender/accent info, and a play button that plays `preview_url` so the user can listen before choosing. Pass the selected `id` as `voice_id` in `POST /sessions`.

---

### GET `/voices/{voice_id}`

**Purpose:** Get full details of a specific voice profile.

**Response (200):** Single `VoiceProfileResponse` object.

**Frontend Use Case:** Displayed when the user taps on a voice card to see detailed information (language, accent, description, preview) before selecting it.

---

## 18. Materials & File Upload

### POST `/materials/upload` 🔒

**Purpose:** Upload a study material file. The platform automatically extracts and stores text content from the file — PDFs via PyMuPDF, DOCX via python-docx, TXT natively, and images via OCR. The extracted content can then be injected into a session's AI teaching context by passing the material's `id` in `material_ids` when creating a session.

**Request (multipart/form-data):**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Max 50 MB. Supported: `.pdf`, `.docx`, `.doc`, `.txt`, `.png`, `.jpg`, `.jpeg` |
| `session_id` | UUID (form field) | ❌ | Optionally associate the upload with an existing session |

**Response (201):**
```json
{
  "success": true,
  "message": "Material uploaded and processed",
  "data": {
    "id": "material-uuid",
    "user_id": "3d6f8b2a-...",
    "session_id": null,
    "file_name": "chapter4_notes.pdf",
    "file_type": "pdf",
    "file_size": 204800,
    "extracted_content": "Chapter 4: Quadratic Equations\n\nA quadratic equation is a polynomial equation of degree 2 in the form ax² + bx + c = 0...",
    "processed": true,
    "created_at": "2026-03-17T10:10:00Z"
  }
}
```

`file_size` is in bytes.

If `processed: false`, text extraction failed (e.g., a scanned PDF with no text layer). The file is still saved and accessible but its content won't be usable in sessions.

**Frontend Use Case:**
- On the "New Session" creation screen: an "Add Material" button lets the student upload textbook chapters, class notes, or reference PDFs. The response `id` is collected and passed in `material_ids` when the session is created — the AI tutor then references the material content while teaching.
- On the "My Library" screen: drag-and-drop or file picker to build a reusable material library for future sessions.

---

### GET `/materials` 🔒

**Purpose:** List all materials uploaded by the authenticated user, paginated and sorted by most recently uploaded first.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Items per page (max 100) |

**Response (200):**
```json
{
  "success": true,
  "message": "Materials retrieved",
  "data": {
    "materials": [
      {
        "id": "material-uuid",
        "file_name": "chapter4_notes.pdf",
        "file_type": "pdf",
        "file_size": 204800,
        "extracted_content": "Chapter 4: Quadratic Equations...",
        "processed": true,
        "session_id": null,
        "created_at": "2026-03-17T10:10:00Z"
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20
  }
}
```

**Frontend Use Case:** The "My Library" / "My Materials" screen. Displays all previously uploaded files. From this screen the student can select existing materials to attach to a new session without re-uploading them.

---

### DELETE `/materials/{material_id}` 🔒

**Purpose:** Delete a previously uploaded material. Only the owner can delete their own materials.

**URL Path Parameters:**

| Param | Type | Description |
|---|---|---|
| `material_id` | UUID | The material to delete |

**Response (200):**
```json
{
  "success": true,
  "message": "Material deleted",
  "data": { "id": "material-uuid" }
}
```

**Response (404):**
```json
{
  "success": false,
  "message": "Material not found",
  "data": null
}
```

**Frontend Use Case:** The delete / trash icon on each material card in the "My Library" screen. Show a brief confirmation before calling. Remove the card from the list on success.

---

## 19. WebSocket — Real-Time Session

### `ws://localhost:8000/api/v1/ws/session/{session_id}`

**Purpose:** Real-time bidirectional channel for the live tutoring session. Handles all time-sensitive interactions: hand raises, chat, config changes mid-session, and MCQ feedback — all with immediate server responses without the overhead of individual HTTP requests.

**Connection Flow:**
1. Open WebSocket connection with the session endpoint
2. Immediately send `authenticate` with the current JWT access token
3. Wait for `authenticated` confirmation before sending any other messages
4. Exchange session messages throughout the session lifecycle

---

**Client → Server messages:**

```json
{ "action": "authenticate", "token": "eyJ..." }
```

```json
{ "action": "hand_raise", "timestamp": 120 }
```

```json
{ "action": "chat", "message": "Can you repeat that?", "is_doubt": false }
```

```json
{ "action": "doubt_resolved" }
```

```json
{ "action": "go_ahead" }
```

```json
{ "action": "config_change", "changes": { "mood": "exam_prep", "personality": "motivational" } }
```

```json
{ "action": "mcq_answer", "is_correct": true }
```

```json
{ "action": "ping" }
```

---

**Server → Client messages:**

| `type` | Triggered When | Payload |
|---|---|---|
| `authenticated` | Auth succeeded | `{ "user_id": "..." }` |
| `hand_raise_ack` | Hand raise received by server | `{ "message": "I see you...", "session_paused": true }` |
| `doubt_response` | AI has answered the submitted doubt | `{ "response": "...", "doubt_id": "..." }` |
| `chat_response` | AI replied to a chat message | `{ "response": "...", "timestamp": 520 }` |
| `doubt_resolved` | Teaching resumes after doubt resolved | `{ "message": "Great! Let's continue..." }` |
| `config_updated` | Config change was applied | `{ "applied": { "mood": "exam_prep" } }` |
| `celebration` | Student answered MCQ correctly | `{ "message": "Excellent! 🎉", "score_delta": 10 }` |
| `mcq_feedback` | Student answered MCQ incorrectly | `{ "message": "Not quite...", "explanation": "..." }` |
| `pong` | Response to ping | `{}` |
| `error` | Any error on the server | `{ "message": "Session not found" }` |

**Frontend Use Case:** Establish the WebSocket connection immediately after `POST /sessions/{id}/start`. Keep it open for the entire session duration. Use it for all real-time events (hand raise, chat, config) where latency matters. The standard REST endpoints remain available for non-real-time operations (session listing, content generation, notes).

---

## 20. User Stats

### GET `/users/me/stats` 🔒

**Purpose:** Retrieve aggregated learning statistics for the authenticated user's dashboard.

**Request:** No body. Authorization header only.

**Response (200):**
```json
{
  "success": true,
  "message": "Stats retrieved",
  "data": {
    "hours_studied": 42.5,
    "day_streak": 7,
    "topics_mastered": 23,
    "avg_score": 87.4,
    "weekly_hours": [3.5, 4.0, 2.0, 5.5, 0.0, 1.0, 3.0]
  }
}
```

| Field | Description |
|---|---|
| `hours_studied` | Total hours spent in completed sessions (rounded to 2 decimal places) |
| `day_streak` | Number of consecutive calendar days (UTC) up to today with at least one completed session |
| `topics_mastered` | Count of distinct `concept_name` values where `completion_percentage ≥ 80%` |
| `avg_score` | Mean `completion_percentage` across all completed sessions |
| `weekly_hours` | 7-element array (Mon–Sun, current UTC week) — hours studied per day, e.g. `[3.5, 4.0, 2.0, 5.5, 0.0, 1.0, 3.0]` |

**Frontend Use Case:** The home dashboard / stats screen. Render:
- `hours_studied` as a large headline number with "hours" unit
- `day_streak` with a flame icon and "day streak" label
- `topics_mastered` as a count card
- `avg_score` as a circular progress indicator (0–100)
- `weekly_hours` as a bar chart with Mon–Sun labels

---

## 21. Error Codes

All errors use the standard response envelope with `success: false`.

| HTTP Code | Meaning | Common Causes |
|---|---|---|
| `400` | Bad Request | Invalid field values, TOTP code wrong, 2FA already enabled/disabled, file too large |
| `401` | Unauthorized | Missing Bearer token, expired token, or token already blacklisted (post-logout) |
| `403` | Forbidden | Accessing or modifying another user's resource |
| `404` | Not Found | Session, material, board, chapter, topic, or voice does not exist |
| `409` | Conflict | Duplicate email on registration |
| `422` | Validation Error | Pydantic schema validation failure — wrong data types or missing required fields |
| `429` | Rate Limited | Auth endpoints: 5/min • Session creation: 10/min • General: 60/min |
| `500` | Internal Server Error | Unexpected server-side failure — check logs |

---

## Appendix: Teaching Content Markers

The AI tutor embeds structured visual and audio cue markers directly within `content_script` text. These are parsed by the backend's `parse_script_to_sse_events` function and emitted as typed SSE events — the frontend does **not** need to parse raw markers from the script itself when using the streaming endpoint.

The markers are documented here for reference (e.g. when working with `content_script` directly from `GET /sessions/{id}`).

### Animation / Whiteboard Markers → `whiteboard` SSE event
```
[ANIMATION: type=diagram, description=Show a simple diagram of carbon-based molecules]
[ANIMATION: type=equation, description=D = b^2 - 4ac]
[ANIMATION: type=list, description=Three types of roots based on discriminant value]
[ANIMATION: type=graph, description=Parabola y=x^2-4x+3 with roots highlighted]
```

Emitted as:
```json
{"type": "whiteboard", "action": "draw", "content_type": "diagram", "description": "...", "id": "wb_1_1"}
```

### Pause Markers → `pause` SSE event (duration in ms)
```
<pause:400ms>     — short breathing pause between sentences
<pause:1500ms>    — dramatic pause before a key concept
```

Emitted as:
```json
{"type": "pause", "duration": 400}
```

### Emotion Tags → `emotion` SSE event
```
[warm]        — warm, encouraging tone
[curious]     — questioning, rising inflection
[calm]        — lower, measured pace
[excited]     — high energy
[serious]     — authoritative
[friendly]    — conversational
```

Emitted as:
```json
{"type": "emotion", "value": "warm"}
```

The `emotion` value persists across all following `text` events until a new emotion tag is encountered. The frontend maps it to Web Speech API pitch + rate delta adjustments.

See [SESSION_STREAMING_README.md](SESSION_STREAMING_README.md) for the complete emotion → voice settings mapping table (Web Speech API pitch/rate).
