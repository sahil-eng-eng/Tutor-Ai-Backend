# Backend Changes for Frontend Compatibility

This document describes all backend changes made to align the API with what the frontend expects.

---

## 1. Auth — Forgot / Reset Password

### Added `POST /auth/forgot-password`
**Request body:** `{ "email": "user@example.com" }`  
**Response:** `{ "success": true, "message": "Password reset email sent" }`

Generates a secure random token (32 bytes URL-safe), stores it on the User model with a 1-hour expiry, and triggers `send_password_reset_email`.

### Added `POST /auth/reset-password`
**Request body:** `{ "token": "<reset_token>", "new_password": "newpass123" }`  
**Response:** `{ "success": true, "message": "Password reset successfully" }`

Looks up the user by the reset token, validates expiry, hashes and sets the new password, then clears the token fields.

**New User model columns:** `reset_password_token (VARCHAR 128)`, `reset_password_expires (TIMESTAMPTZ)`

---

## 2. Auth — Verify Account Schema Fix

### `POST /auth/verify`
**Old request body:** `{ "email": "...", "code": "..." }`  
**New request body:** `{ "token": "<verification_token>" }`

The frontend receives only the token from the email link. The backend now looks up the user by `verification_code == token`.

---

## 3. Auth — Resend Verification Body Fix

### `POST /auth/resend-verification`
**Old:** Query parameter `?email=`  
**New request body:** `{ "email": "user@example.com" }`

---

## 4. Sessions — SSE Token Auth

### `GET /sessions/{id}/segments/{order}/stream`
The SSE stream now accepts authentication via a `?token=<access_token>` query parameter in addition to the `Authorization: Bearer <token>` header. This is required because the browser `EventSource` API cannot set custom headers.

---

## 5. Sessions — Playlists List Endpoint

### Added `GET /sessions/playlists`
**Query params:** `page` (default 1), `page_size` (default 20)  
**Response:**
```json
{
  "playlists": [
    {
      "id": "...",
      "title": "...",
      "concept_name": "...",
      "total_sessions": 5,
      "completed_sessions": 2,
      "is_complete": false,
      "created_at": "..."
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

Route is registered **before** `/{session_id}` to prevent route shadowing.

---

## 6. Sessions — subject_name in Session List

### `GET /sessions`
`SessionResponse` now includes an optional `subject_name: string | null` field.  
The list query does an `OUTER JOIN` with `curriculum_subjects` and populates `subject_name` from `Subject.name`.

---

## 7. Sessions — Config Patch Response Shape

### `PATCH /sessions/{id}/config`
**Response data shape** changed from full config object to:
```json
{ "session_id": "...", "applied": { ...config fields... } }
```

---

## 8. User Stats Endpoint

### Added `GET /users/me/stats`
**Response:**
```json
{
  "hours_studied": 42.5,
  "day_streak": 7,
  "topics_mastered": 23,
  "avg_score": 87.4,
  "weekly_hours": [3.5, 4.0, 2.0, 5.5, 0.0, 1.0, 3.0]
}
```

- `hours_studied`: Sum of `total_duration_seconds` of completed sessions ÷ 3600
- `day_streak`: Consecutive calendar days (UTC) ending today with ≥1 completed session
- `topics_mastered`: Count of distinct `concept_name` values where `completion_percentage >= 80`
- `avg_score`: Mean `completion_percentage` across all completed sessions
- `weekly_hours`: 7-element array (Mon–Sun, current UTC week) of hours studied per day

---

## 9. 2FA Response Shape Fix

### `POST /users/me/2fa/confirm`
**Old response data:** `null`  
**New response data:** `{ "message": "2FA enabled successfully", "is_2fa_enabled": true }`

### `POST /users/me/2fa/disable`
**Old response data:** `null`  
**New response data:** `{ "message": "2FA disabled successfully", "is_2fa_enabled": false }`

### `TOTPConfirm` schema field rename
**Old field name:** `code`  
**New field name:** `totp_code`

Frontend must send `{ "totp_code": "123456" }` to both confirm and disable endpoints.

---

## 10. Pulse — Record Endpoint Body Fix

### `POST /interactions/pulse/{session_id}/record`
**Old:** Query parameters `metric_type`, `score`, `max_score`, `timestamp_seconds`  
**New request body:**
```json
{
  "focus_level": 75.0,
  "notes": "Optional notes about current attention",
  "timestamp_in_session_seconds": 300
}
```

`focus_level` is mapped internally to `metric_type="focus"` with `score=focus_level`.

---

## 11. Pulse — Adjust Field Rename

### `POST /interactions/pulse/{session_id}/adjust`
**Old field name:** `delta`  
**New field name:** `adjustment`

**New request body:**
```json
{
  "adjustment": 10.0,
  "reason": "User answered correctly",
  "timestamp_in_session_seconds": 450
}
```

Range remains `-50` to `+50`.

---

## 12. Materials — file_size Field

### `POST /materials/upload`
Response now includes `file_size: number` (file size in bytes).

**New UserMaterial model column:** `file_size (INTEGER, nullable)`

File size is recorded at upload time from the raw bytes content length.

---

## 13. Materials — Paginated List Response

### `GET /materials`
**Old response data:** flat array of material objects  
**New response data:**
```json
{
  "materials": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Query params:** `page` (default 1), `page_size` (default 20)

---

## 14. Materials — Delete Endpoint

### Added `DELETE /materials/{material_id}`
Deletes the specified material if it belongs to the current user.  
Returns 404 if not found or not owned by the user.  
**Response:** `{ "success": true, "data": { "id": "..." }, "message": "Material deleted" }`

---

## 15. Speech / TTS Contract

### `POST /speech/enrich`
Enriches plain text with SSML-style markers for natural TTS delivery.

**Request body:**
```json
{
  "text": "The mitochondria is the powerhouse of the cell.",
  "context": "biology lesson for 10th grade"
}
```

**Response:**
```json
{
  "enriched_text": "The mitochondria... [pause] is the powerhouse of the cell.",
  "markers": [...]
}
```

### `POST /speech/voice-params`
Computes optimal ElevenLabs `voice_settings` parameters for a given teaching context.

**Request body:**
```json
{
  "mood": "FOCUSED",
  "personality": "SOCRATIC",
  "language": "english"
}
```

**Response:**
```json
{
  "stability": 0.7,
  "similarity_boost": 0.8,
  "style": 0.4,
  "use_speaker_boost": true
}
```

---

## Database Migrations

A new Alembic migration (`26932420b887_add_reset_password_tokens_and_file_size`) was created and applied, adding:

| Table | Column | Type |
|---|---|---|
| `users` | `reset_password_token` | `VARCHAR(128)` |
| `users` | `reset_password_expires` | `TIMESTAMPTZ` |
| `user_materials` | `file_size` | `INTEGER` |

---

## Summary of Files Changed

| File | Changes |
|---|---|
| `app/models/user.py` | Added `reset_password_token`, `reset_password_expires` |
| `app/models/material.py` | Added `file_size` column |
| `app/schemas/user.py` | Added `ForgotPassword`, `ResetPassword`, `ResendVerification`; changed `VerifyAccount` to `{token}` |
| `app/schemas/curriculum.py` | Added `file_size` to `MaterialUploadResponse` |
| `app/schemas/interaction.py` | Added `PulseRecordRequest`; renamed `delta` → `adjustment` in `PulseAdjustRequest` |
| `app/schemas/session.py` | Added `subject_name` to `SessionResponse` |
| `app/services/auth_service.py` | Added `forgot_password`, `reset_password`; fixed `verify_account` to use token |
| `app/services/session_service.py` | Added `list_playlists`; updated `list_sessions` to join Subject for `subject_name` |
| `app/services/user_service.py` | Added `get_stats` method |
| `app/api/v1/auth.py` | Added forgot-password, reset-password routes; fixed verify/resend schemas |
| `app/api/v1/sessions.py` | Added SSE token auth helper; added `/playlists` list route; fixed config response shape |
| `app/api/v1/users.py` | Added `/me/stats` endpoint; fixed 2FA responses; renamed `TOTPConfirm.code` → `totp_code` |
| `app/api/v1/interactions.py` | Fixed pulse record body; fixed pulse adjust field name |
| `app/api/v1/materials.py` | Added `file_size` on upload; paginated list; added DELETE endpoint |
| `alembic/env.py` | Escaped `%` in DATABASE_URL for configparser compatibility |
| `alembic/versions/26932420b887_...py` | New migration for 3 new columns |
