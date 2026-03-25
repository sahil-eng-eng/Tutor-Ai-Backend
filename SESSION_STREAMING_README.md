# Session Streaming Architecture

End-to-end guide covering the session lifecycle, N+1 segment prefetch strategy, structured SSE streaming, WPM-based content length, pause/resume with chunk tracking, live doubt streaming, pulse management, and frontend integration (including TTS with ElevenLabs).

**Base URL:** `http://localhost:8000/api/v1`

---

## Table of Contents

1. [Session Lifecycle Overview](#1-session-lifecycle-overview)
2. [Create Session](#2-create-session)
3. [Preview & Edit Evaluation](#3-preview--edit-evaluation)
4. [Start Session](#4-start-session)
5. [SSE Streaming — Segment Teaching](#5-sse-streaming--segment-teaching)
6. [N+1 Prefetch Architecture](#6-n1-prefetch-architecture)
7. [SSE Event Reference](#7-sse-event-reference)
8. [WPM-Based Content Length](#8-wpm-based-content-length)
9. [Pause & Resume with Chunk Tracking](#9-pause--resume-with-chunk-tracking)
10. [Mid-Session Config Changes](#10-mid-session-config-changes)
11. [Segment Switching Flow](#11-segment-switching-flow)
12. [Live Doubt Streaming](#12-live-doubt-streaming)
13. [Session Completion Flow](#13-session-completion-flow)
14. [Pulse Meter Integration](#14-pulse-meter-integration)
15. [Frontend TTS Integration (ElevenLabs)](#15-frontend-tts-integration-elevenlabs)
16. [Frontend Whiteboard Rendering](#16-frontend-whiteboard-rendering)
17. [Error Handling](#17-error-handling)
18. [Full Sequence Diagram](#18-full-sequence-diagram)
19. [Backend vs Frontend Responsibilities](#19-backend-vs-frontend-responsibilities)

---

## 1. Session Lifecycle Overview

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌────────────┐     ┌───────────┐
│  CREATE   │────>│ PREVIEW  │────>│    START     │────>│ SSE STREAM │────>│ COMPLETE  │
│  (draft)  │     │ (draft)  │     │(in_progress) │     │ per segment│     │           │
└──────────┘     └──────────┘     └──────────────┘     └────────────┘     └───────────┘
      │                │               │                     │                  │
      │           Edit eval       Builds DB           Streams events       Goodbye msg
      │           (optional)      segments +          + prefetches N+1     generated
      │                           generates seg 1
```

| Step | Endpoint | What Happens |
|------|----------|--------------|
| **Create** | `POST /sessions` | AI evaluates inputs → produces `session_evaluation` JSON with segment plan. Status = `draft`. |
| **Preview** | `GET /sessions/{id}/preview` | Returns `session_evaluation` for the frontend to display/edit segment topics, durations, order. |
| **Edit Evaluation** | `PUT /sessions/{id}/evaluation` | Frontend sends modified `session_evaluation` back. Only allowed in `draft`/`ready` status. |
| **Start** | `POST /sessions/{id}/start` | Builds `SessionSegment` DB rows from evaluation. Generates `content_script` for **segment 1 only**. Status → `in_progress`. |
| **Stream** | `GET /sessions/{id}/segments/{order}/stream` | Streams segment N's `content_script` as structured SSE events. Background-prefetches segment N+1. |
| **Pause** | `POST /sessions/{id}/pause` | Status → `paused`. Frontend can resume with `POST /sessions/{id}/start`. |
| **End** | `POST /sessions/{id}/end` | AI generates a goodbye message. Status → `completed`. |
| **Config** | `PATCH /sessions/{id}/config` | Update mood/personality/language/voice mid-session. Invalidates pending segment content. |

---

## 2. Create Session

### `POST /sessions`

Creates a session with AI-generated segment planning.

**Request:**
```json
{
  "user_profession": "college_student",
  "concept_name": "Organic Chemistry — Carbon Bonding",
  "study_level": "intermediate",
  "entire_session_type": "in_depth",
  "session_mode": "single_session",
  "duration_type": "user_defined",
  "duration_minutes": 45,
  "mood": "focused",
  "model_personality": "very_friendly",
  "language": "English",
  "university": "MIT",
  "course": "Chemistry 101",
  "semester": 3,
  "material_ids": ["uuid-of-uploaded-pdf"]
}
```

**Response:** Standard envelope with `data` containing the full session object including `session_evaluation`:

```json
{
  "success": true,
  "data": {
    "id": "abc-123",
    "status": "draft",
    "concept_name": "Organic Chemistry — Carbon Bonding",
    "session_evaluation": {
      "session_overview": {
        "main_concept": "Carbon Bonding",
        "estimated_total_duration_seconds": 2700,
        "difficulty_rating": 3,
        "prerequisites": ["Basic atomic structure"]
      },
      "segments": [
        {
          "segment_order": 1,
          "segment_type": "introduction",
          "title": "Welcome & Carbon Basics",
          "key_points": ["Why carbon is special", "Tetravalency"],
          "duration_seconds": 300,
          "teaching_approach": "Start with a warm greeting and relatable analogy",
          "visual_aids": ["carbon_atom_diagram"]
        },
        {
          "segment_order": 2,
          "segment_type": "core_teaching",
          "title": "Single, Double & Triple Bonds",
          "key_points": ["Bond types", "Hybridization basics"],
          "duration_seconds": 600,
          "teaching_approach": "Visual comparison with whiteboard diagrams"
        }
      ],
      "teaching_strategy": {
        "personality_approach": "Warm and encouraging",
        "mood_adaptation": "Maintain focused energy",
        "engagement_techniques": ["analogies", "visual aids", "check-in questions"]
      }
    }
  }
}
```

---

## 3. Preview & Edit Evaluation

### `GET /sessions/{id}/preview`

Returns the `session_evaluation` JSON so the frontend can display a segment-by-segment preview before starting.

### `PUT /sessions/{id}/evaluation`

Frontend sends back the edited evaluation. The backend recalculates `total_duration_seconds` from the updated segments.

```json
{
  "session_evaluation": {
    "session_overview": { ... },
    "segments": [
      { "segment_order": 1, "title": "Updated Intro", "duration_seconds": 400, ... },
      { "segment_order": 2, "title": "Core: Bond Types", "duration_seconds": 600, ... }
    ]
  }
}
```

> Only allowed when status is `draft` or `ready`. Returns `400` after `start`.

---

## 4. Start Session

### `POST /sessions/{id}/start`

**What happens internally:**
1. Reads `session_evaluation.segments` → creates `SessionSegment` DB rows.
2. Generates `content_script` for **segment 1 only** (via AI).
3. Sets all other segments to `PENDING` with `content_script = null`.
4. Recomposes `system_prompt_snapshot` with full session context.
5. Status → `in_progress`.

**Response:** Full `SessionDetailResponse` including segments array (segment 1 has `content_script`, others are null).

**Why only segment 1?** Generating all segments upfront wastes time and API calls. The user may change config mid-session, invalidating pre-generated content. The N+1 prefetch strategy (see below) ensures each segment is ready just-in-time.

---

## 5. SSE Streaming — Segment Teaching

### `GET /sessions/{id}/segments/{order}/stream`

Streams a segment's teaching content as **Server-Sent Events**.

**Authentication:** Since `EventSource` doesn't support custom headers, this endpoint accepts auth two ways:

| Method | Example |
|--------|---------|
| Header | `Authorization: Bearer <jwt>` |
| Query param | `?token=<jwt>` |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_chunk` | int | `0` | Resume stream from this chunk number. `0` = from the start. |

**Frontend connection (JavaScript):**
```javascript
const eventSource = new EventSource(
  `/api/v1/sessions/${sessionId}/segments/${segmentOrder}/stream?token=${jwt}`
);

let lastChunk = 0;  // track for pause/resume

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  lastChunk = data.chunk ?? lastChunk;  // always update
  
  switch (data.type) {
    case 'segment_start':
      console.log(`Starting: ${data.title} (${data.duration_seconds}s)`);
      break;
    case 'emotion':
      updateTutorEmotion(data.value);  // Change avatar/voice
      break;
    case 'text':
      queueForTTS(data.value);          // Send sentence to ElevenLabs
      break;
    case 'pause':
      insertSilence(data.duration);     // Wait before next TTS
      break;
    case 'whiteboard':
      renderWhiteboard(data);           // Draw diagram/animation
      break;
    case 'segment_end':
      onSegmentComplete(data.segment_order);
      break;
    case 'session_end':
      onSessionComplete(data.session_id);
      break;
    case 'error':
      handleError(data.code, data.message);
      break;
  }
};
```

**Response headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

## 6. N+1 Prefetch Architecture

The backend uses a look-ahead strategy to ensure each segment's content is ready before the frontend requests it.

```
Timeline:

POST /start
  └─> Generate segment 1 content_script (synchronous, AI call)
      └─> Response: session started, segment 1 ready

GET /segments/1/stream
  ├─> Stream segment 1 (content_script already exists)
  └─> Fire background task: generate segment 2 content_script
      └─> asyncio.create_task(_background_prefetch_segment(session_id, user_id, 2))

GET /segments/2/stream
  ├─> content_script exists? → stream immediately
  │   (background task finished before frontend requested)
  ├─> content_script null? → wait up to 15s (polling DB every 0.5–2s)
  │   └─> still null after 15s? → generate synchronously (fallback)
  └─> Fire background task: generate segment 3 content_script

GET /segments/3/stream
  └─> ... same pattern ...

GET /segments/N/stream  (last segment)
  ├─> Stream content
  ├─> NO background prefetch (nothing after last segment)
  └─> Emits segment_end + session_end events
```

### How the background prefetch works

```python
async def _background_prefetch_segment(session_id, user_id, segment_order):
    """Runs as fire-and-forget asyncio.Task with independent DB session."""
    
    # 1. Open independent DB session (not the request-scoped one)
    async with AsyncSessionLocal() as db:
        # 2. Load session and find target segment
        # 3. Skip if content_script already exists
        # 4. Get previous segment summary (first 800 chars) for AI context
        # 5. Get material summary for AI context
        # 6. Generate content via AI
        # 7. db.refresh(target) — detect if config changed while generating
        # 8. If target.content_script is STILL null → write it, commit
        #    If someone else wrote it → discard, don't overwrite
```

### Wait logic when content isn't ready

When the frontend requests segment N and the background prefetch hasn't finished:

1. Backend polls the DB with exponential backoff:
   - Start: 0.5s interval
   - Growth: ×1.5 per poll
   - Cap: 2.0s max interval
   - Timeout: 15s total
2. Uses an **independent DB session** (separate from the request session) so it can see commits from the background task.
3. If still not ready after 15s → generates synchronously (the user waits, but streaming still works).

### Previous segment context

Each segment's `content_script` is generated with awareness of the previous segment:

- The first **800 characters** of the previous segment's `content_script` are passed to the AI prompt as `previous_segment_summary`.
- This ensures topical continuity, smooth transitions, and no repeated content.

---

## 7. SSE Event Reference

Every event is a JSON object wrapped in `data: {json}\n\n` format.

> **All events include a `chunk` integer field.** The frontend stores this to enable pause/resume. `segment_start` always has `chunk: 0`; content events start at `chunk: 1` and increment by 1 for each event.

### `segment_start`
First event of every segment. Always emitted — even when resuming with `from_chunk > 0`. Chunk is always `0`.
```json
{
  "type": "segment_start",
  "segment_order": 1,
  "title": "Welcome & Carbon Basics",
  "duration_seconds": 300,
  "total_segments": 5,
  "chunk": 0
}
```

### `emotion`
Tutor emotion change. Frontend should update avatar expression and voice settings.
```json
{ "type": "emotion", "value": "warm", "chunk": 1 }
```
Valid values: `warm`, `curious`, `calm`, `excited`, `serious`, `friendly`, `neutral`.

### `text`
A single sentence of spoken content. Frontend queues this for TTS.
```json
{ "type": "text", "value": "Carbon is unique because it can form four bonds.", "chunk": 2 }
```

### `pause`
Silence between sentences. Frontend inserts a delay before the next TTS call.
```json
{ "type": "pause", "duration": 400, "chunk": 3 }
```
Duration in milliseconds.

### `whiteboard`
Visual content to render on screen. Frontend draws/animates based on `content_type`.
```json
{
  "type": "whiteboard",
  "action": "draw",
  "content_type": "diagram",
  "description": "Show carbon atom with 4 bonding electrons",
  "id": "wb_1_1",
  "chunk": 4
}
```
`id` format: `wb_{segment_order}_{counter}`. Use this to track which visuals are active.

### `segment_end`
Last content event of every segment.
```json
{ "type": "segment_end", "segment_order": 1, "chunk": 47 }
```

### `session_end`
Only emitted after the **last segment** completes. Signals the entire session is done.
```json
{ "type": "session_end", "session_id": "abc-123-uuid", "chunk": 48 }
```

### `error`
Emitted if something goes wrong during streaming.
```json
{ "type": "error", "code": "not_found", "message": "Segment 5 not found" }
```
Error codes: `not_found`, `bad_request`, `server_error`.

---

## 8. WPM-Based Content Length

Every segment's AI-generated `content_script` is told how many words to produce, matching the segment's declared `duration_seconds` at a speaking pace appropriate for the tutor's personality and the student's current mood.

### WPM targets

| Words Per Minute | Personalities | Moods |
|-----------------|---------------|-------|
| **130 WPM** (slow, natural pace) | `very_friendly`, `funny`, `storyteller`, `patient` | `tired`, `light` |
| **150 WPM** (default) | All others | All others |
| **165 WPM** (brisk, energetic) | `strict`, `motivational`, `attentive` | `focused`, `very_focused`, `exam_prep` |

### Formula

```
target_word_count = round(wpm × duration_seconds / 60)
```

**Example:** A 5-minute (300s) segment with `mood = focused` and `personality = attentive`:
- WPM = 165
- Target = round(165 × 300 / 60) = **825 words**

The AI prompt includes an explicit instruction:
> *"TARGET CONTENT LENGTH: Write approximately 825 words for this segment. This matches the 300s duration at the expected speaking pace. Adjust depth, examples, and elaboration to hit this target — do not cut short."*

The `max_tokens` budget for segment generation is **8192** to accommodate longer segments.

---

## 9. Pause & Resume — Client-Side Buffer Replay

### Problem
The backend reads `content_script` from the database and yields ALL SSE events nearly instantly (~1ms total). This means `segment_end` always arrives before TTS finishes speaking the first sentence. Previous approaches using `from_chunk` to re-hit the backend on resume caused the segment to auto-advance because `segment_end` → `markSegmentEnd()` resolved on an empty audio queue.

### Solution: Client-side event buffering
The frontend buffers **all** SSE events from the backend on first connect. Pause/resume operates entirely on the local buffer — no backend SSE endpoint is re-hit.

```
connectSSE():
  1. Open EventSource → receive ALL events → push into sseBufferRef[]
  2. On segment_end/session_end received → close EventSource
  3. Call replayFromBuffer(0) to feed events into the TTS audio queue

replayFromBuffer(fromIndex):
  1. Count remaining text words → calibrateRate(words, duration)
  2. For each event from sseBufferRef[fromIndex..]:
     - "text"       → audioQueue.enqueueText()  [onEnd updates playbackIndexRef]
     - "emotion"    → audioQueue.setEmotion()
     - "pause"      → audioQueue.enqueueSilence()
     - "whiteboard" → setWhiteboardItems()
     - "segment_end"→ audioQueue.markSegmentEnd().then(advance)

handlePause:
  Pause:  audioQueue.clear() + save playbackIndexRef (auto-tracked by TTS onEnd)
  Resume: startMutation + replayFromBuffer(playbackIndexRef.current)
          NO connectSSE, NO backend re-hit

handleHandRaise:
  Raise:  same as pause (stop TTS, index saved)
  Lower:  startMutation + replayFromBuffer(playbackIndexRef.current)
```

### Key refs
| Ref | Purpose |
|-----|---------|
| `sseBufferRef` | `SSEEvent[]` — stores all events from backend |
| `playbackIndexRef` | `number` — next event index for TTS to process |
| `lastChunkRef` | `number` — last received SSE chunk number (for page-refresh resilience) |

### Backend status flow (unchanged)
- `POST /sessions/{id}/pause` → status = `paused`
- `POST /sessions/{id}/start` → status = `in_progress`
- The backend marks a segment `COMPLETED` after the full SSE generator finishes, regardless of frontend state.

> **Note:** The `from_chunk` query parameter on the stream endpoint still works correctly (verified with tests), but it is no longer used by the frontend. The buffer-replay approach eliminates the timing race entirely.

---

## 10. Mid-Session Config Changes

### `PATCH /sessions/{id}/config`

Users can change mood, personality, language, study level, or voice mid-session.

```json
{
  "mood": "very_focused",
  "model_personality": "motivational",
  "study_level": "advanced"
}
```

**What happens internally:**
1. Session fields are updated.
2. `SessionConfig` record is updated.
3. `system_prompt_snapshot` is recomposed with the new config.
4. **All PENDING segments with pre-generated `content_script` are invalidated** (`content_script` set to `null`).
5. The next time those segments are streamed, the background prefetch or sync fallback generates fresh content using the **new** config.

**Race condition handling:** If a background prefetch task is mid-flight when the config changes:
- The prefetch uses `db.refresh(target)` before writing to detect if the segment was invalidated.
- If `content_script` was set to `null` by the config update, the prefetch discards its result (generated with old config).
- The next SSE request triggers a fresh generation with the new config.

**Frontend note:** Call this endpoint between segments, not during active streaming. The current segment continues streaming with the old config. Changes take effect starting from the **next** segment.

---

## 11. Segment Switching Flow

The **frontend** controls segment transitions. The backend does not auto-advance.

```
1. Frontend connects to GET /segments/1/stream
2. Receives events... segment_end arrives
3. Frontend: close EventSource for segment 1
4. Frontend decides when to start segment 2 (user click, timer, auto-play)
5. Frontend connects to GET /segments/2/stream
   └─> Backend either has content ready (prefetched) or waits/generates
6. Repeat until session_end
```

**Frontend responsibilities:**
- Close the `EventSource` connection after `segment_end`.
- Optionally show an interstitial UI (progress bar, "Ready for next topic?").
- Record any pulse data between segments.
- Open a new `EventSource` for the next segment order.

**No backend call needed between segments** — just connect to the next SSE endpoint. The N+1 prefetch ensures content is likely already ready.

---

## 12. Live Doubt Streaming

Students can raise a doubt during active segment playback. The backend streams an AI-generated answer in real time as SSE events, using the segment's `content_script` as context.

### `POST /interactions/doubts/{session_id}/stream-answer`

**Authentication:** `Authorization: Bearer <jwt>` header **or** `?token=<jwt>` query param.

**Request body:**
```json
{
  "query_text": "Why does carbon form 4 bonds instead of 2?",
  "segment_order": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query_text` | string | Yes | Student's question (3–2000 chars) |
| `segment_order` | int | No | Segment providing context. Defaults to the active `IN_PROGRESS` segment. |

**SSE Event sequence:**

```
data: {"type": "doubt_start", "query": "Why does carbon form 4 bonds?"}

data: {"type": "text", "value": "Great question!", "chunk": 1}

data: {"type": "text", "value": "Carbon has 4 valence electrons, meaning it needs 4 more to complete its outer shell.", "chunk": 2}

data: {"type": "text", "value": "This is why forming 4 covalent bonds is the most stable configuration.", "chunk": 3}

data: {"type": "doubt_end", "chunk": 4}
```

**Events:**

| Event | Description |
|-------|-------------|
| `doubt_start` | Signals streaming has started. Contains the original `query` text. |
| `text` | One complete sentence of the AI answer. Send to TTS. Includes `chunk` counter. |
| `doubt_end` | Streaming complete. |
| `error` | Stream failed. Contains `code` and `message`. |

**Pulse:** On completion (whether user disconnects or stream ends normally), the student's pulse is incremented by **+4** (`live_doubt_resolved`).

**Context used:** The AI receives:
1. The session's `system_prompt_snapshot` (tutor personality, language, etc.)
2. The first 2000 characters of the active segment's `content_script`
3. The student's `query_text`

**Frontend integration:**
```javascript
// Open EventSource for doubt streaming
const url = `/api/v1/interactions/doubts/${sessionId}/stream-answer?token=${jwt}`;

// POST request body — EventSource only supports GET, so use fetch + ReadableStream
const response = await fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${jwt}` },
  body: JSON.stringify({ query_text: userQuestion, segment_order: currentSegment }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      if (event.type === 'text') queueForTTS(event.value);
      if (event.type === 'doubt_end') closeMicUI();
    }
  }
}
```

> **Note:** Since this is a `POST` endpoint, use `fetch()` with a `ReadableStream` reader instead of `EventSource` (which only supports GET).

---

## 13. Session Completion Flow

### Natural completion (all segments streamed)

1. Last segment's SSE emits `segment_end` then `session_end`.
2. Frontend receives `session_end` → close EventSource.
3. Frontend calls `POST /sessions/{id}/end` to get the goodbye message.
4. Display goodbye message to user.

### Manual end (user exits early)

1. Frontend calls `POST /sessions/{id}/end`.
2. Backend generates an AI goodbye message based on how many segments were completed.
3. Response includes `goodbye_message`, `completion_percentage`.

### Pause and resume

1. `POST /sessions/{id}/pause` → status = `paused`.
2. Later: `POST /sessions/{id}/start` → status = `in_progress` (resumes from where user left off).
3. Frontend tracks which segment was last streamed and connects to the next one.

---

## 14. Pulse Meter Integration

The pulse meter tracks student engagement (0–100, starts at 50). Both the frontend and backend can adjust it.

### Endpoints

| Method | Endpoint | Body | Purpose |
|--------|----------|------|---------|
| `GET` | `/interactions/pulse/{session_id}` | — | Get current pulse percentage & status |
| `POST` | `/interactions/pulse/{session_id}/record` | `{ "focus_level": 75.0, "notes": "..." }` | Record self-reported focus level |
| `POST` | `/interactions/pulse/{session_id}/adjust` | `{ "adjustment": 10.0, "reason": "..." }` | Direct adjustment (-50 to +50) |
| `POST` | `/interactions/pulse/{session_id}/activity` | `?activity_type=hand_raise` | Record activity (auto-adjusts pulse) |

### When to update pulse

| User Action | API Call | Effect |
|-------------|----------|--------|
| Watching for 30s+ without interaction | `adjust` with negative delta | ↓ Pulse |
| Clicking "I understand" or nodding | `adjust` with positive delta | ↑ Pulse |
| Raising hand (hand-raise button) | `POST /interactions/hand-raise` | ↑ Pulse (backend auto-adjusts) |
| Sending a doubt | `POST /interactions/doubts` | ↑ Pulse (engagement signal) |
| Answering MCQ correctly | Backend auto-adjusts after `POST /interactions/mcq/submit` | ↑ Pulse |
| Sending chat message | `POST /interactions/chat` | ↑ Pulse (auto-tracked) |
| Streaming a live doubt answer | Handled internally by backend | ↑ Pulse +4 (live_doubt_resolved) |

### Frontend implementation notes

- Poll `GET /pulse/{session_id}` every 30–60s to sync the meter.
- Or update optimistically on each `adjust` call.
- Show the pulse as a gauge, bar, or ring that animates smoothly.
- When pulse drops below a threshold (e.g., 30), consider showing an MCQ pop-up or engagement prompt.

---

## 15. Frontend TTS Integration (Web Speech API)

**Decision: The frontend manages TTS using the browser's built-in Web Speech API.** No external service (ElevenLabs) is needed — this reduces cost, latency, and dependency.

### Why Web Speech API?
- **Zero cost:** No API keys or paid services required.
- **Low latency:** Audio is synthesized locally in the browser.
- **Emotion control:** `SpeechSynthesisUtterance` supports `rate` and `pitch` adjustments mapped to emotions.
- **Offline support:** Works without internet after the SSE events are buffered.

### Architecture: `useAudioQueue` hook

The TTS system is encapsulated in `src/hooks/useAudioQueue.ts`:

```
useAudioQueue() → {
  enqueueText(text, onStart?, onEnd?)  // Add text to speech queue
  enqueueSilence(durationMs)            // Add a timed pause
  setEmotion(emotion)                   // Adjust pitch/rate delta
  calibrateRate(totalWords, durationSec) // Set base speech rate for segment
  markSegmentEnd() → Promise            // Resolves when queue drains
  clear()                                // Cancel all pending + discard drain
}
```

### Speech rate calibration

Each segment has a known `duration_seconds` and the frontend counts total words in buffered text events:

```
WPM_AT_RATE_1 = 180  (Web Speech API baseline)
neededWpm = (totalWords / durationSeconds) * 60
baseRate = clamp(neededWpm / WPM_AT_RATE_1, 0.7, 1.8)
```

### Emotion → voice adjustment

Instead of absolute rate values, emotions apply a **small delta** on top of the calibrated `baseRate`:

| Emotion | Rate Delta | Pitch |
|---------|-----------|-------|
| warm | -0.04 | 1.05 |
| curious | +0.00 | 1.08 |
| calm | -0.08 | 0.95 |
| excited | +0.06 | 1.12 |
| serious | -0.05 | 0.90 |
| friendly | -0.02 | 1.05 |
| neutral | +0.00 | 1.00 |

Final rate = `clamp(baseRate + emotionDelta, 0.5, 2.5)`

### Gapless batch playback

The audio queue uses a `runLoop` pattern that drains consecutive text items without inter-sentence gaps:

1. `runLoop` pops all consecutive text items from the queue
2. Creates `SpeechSynthesisUtterance` for each, chained via `onend`
3. Only pauses execution for explicit `silence` items
4. `markSegmentEnd` → resolves a Promise when the queue fully drains

Since all SSE events are buffered before replay, the queue receives multiple text items synchronously, enabling true batch playback.

### TTS markup stripping

The backend's `content_script` may contain markers like `[warm]`, `<pause:400ms>`, `WHITEBOARD:...`. These are parsed as structured SSE events by the backend. The `stripTTSMarkup()` function removes any residual markup from text values before speaking or displaying.

---

## 16. Frontend Whiteboard Rendering

Whiteboard events are rendered by the `WhiteboardCanvas` component (`src/components/WhiteboardCanvas.tsx`), which provides animated visual presentation of teaching content.

### Component: `<WhiteboardCanvas>`

```tsx
<WhiteboardCanvas
  items={whiteboardItems}        // ActiveWhiteboardItem[]
  streamingText={streamingText}  // Current TTS sentence being spoken
  sessionTitle={sessionTitle}    // Concept name
  isPaused={isPaused}           // Show paused indicator
/>
```

### Content type rendering

| `content_type` | Rendering |
|----------------|-----------|
| `equation` | **KaTeX** — rendered via `katex.renderToString()` with display mode. Has gradient blue/purple background. |
| `list` | Animated bullet items with staggered fade-in. Supports both `- item` and `1. item` syntax. |
| `code` | Dark background, monospace font, syntax-highlighted code block. |
| `diagram` | Amber gradient card with "Visual" label and description text. |
| `chart` | Same as diagram rendering. |
| `image` | Same as diagram rendering. |
| (text fallback) | Standard text block with primary background. Supports inline `$...$` KaTeX math. |

### Auto-detection heuristics

If the `content_type` doesn't match exactly, the component uses heuristic detection:
- **Equation:** Contains math characters (`=`, `^`, `\frac`, `\sqrt`, etc.)
- **List:** Starts with `- `, `* `, or `1. ` patterns
- **Code:** Contains `{`, `}`, `=>`, `function`, `class`, etc.

### Animation

All whiteboard items use `framer-motion` with `AnimatePresence`:
- Fade-in + slide-up on appear (`y: 20 → 0`, `opacity: 0 → 1`)
- Staggered timing for list items
- Live caption with blinking cursor during TTS
- Paused state shows a pulsing "Session Paused" indicator

### Libraries used

| Library | Purpose |
|---------|---------|
| `katex` (v0.16.40) | LaTeX equation rendering |
| `react-markdown` | Markdown parsing (future use) |
| `remark-math` | Math expression extraction from markdown |
| `rehype-katex` | KaTeX rendering in markdown pipeline |
| `framer-motion` | Animations and transitions |

### Future scalability — Visual services

For richer whiteboard content beyond text/equation rendering, consider these services:

| Service / Library | Use Case | Integration |
|---|---|---|
| **Excalidraw** | Hand-drawn style diagrams, flowcharts | React component, self-hosted |
| **Mermaid.js** | Flowcharts, sequence diagrams, class diagrams from text | `mermaid.render()` from description text |
| **D3.js** | Data visualizations, interactive charts | Custom renderers per chart type |
| **Three.js / React Three Fiber** | 3D visualizations (molecules, geometry) | WebGL-based, works for STEM content |
| **Manim** (backend) | Mathematical animations (like 3Blue1Brown) | Python library, render to video/GIF on backend, send URL via whiteboard event |
| **DALL-E / Stable Diffusion** (backend) | AI-generated diagrams and illustrations | Generate image on backend, send URL in `description` field |
| **Lottie** | Pre-built animations (icons, transitions) | JSON-based animations, lightweight |

**Recommended architecture for scaling:**
1. Backend generates visual content (Manim animations, AI images) and stores URL
2. Whiteboard event `description` contains the URL or structured data
3. Frontend `WhiteboardCanvas` renders based on `content_type` + description format
4. New `content_type` values can be added without breaking existing rendering

---

## 17. Error Handling

### SSE errors

The stream may emit an error event instead of content:

```json
{ "type": "error", "code": "not_found", "message": "Segment 5 not found" }
```

| Code | Cause | Frontend action |
|------|-------|-----------------|
| `not_found` | Invalid segment order or session ID | Show error, check session state |
| `bad_request` | Session not in `in_progress` state | Prompt user to start/resume session |
| `server_error` | Unexpected backend failure | Retry once, then show error UI |

### HTTP errors (non-SSE endpoints)

| Status | Meaning | Typical cause |
|--------|---------|---------------|
| 401 | Unauthorized | Token expired. Refresh and retry. |
| 400 | Bad request | Invalid state transition (e.g., start already-started session). |
| 404 | Not found | Session/segment doesn't exist or belongs to another user. |
| 422 | Validation error | Missing/invalid request body fields. |
| 500 | Server error | Backend bug. Retry or report. |

### EventSource reconnection

The browser's `EventSource` auto-reconnects on network failure. To prevent duplicate content on reconnect, track the last received `segment_order` + event index and skip already-processed events.

---

## 18. Full Sequence Diagram

```
Frontend                               Backend                              AI Service
   │                                      │                                      │
   │── POST /sessions ──────────────────>│                                      │
   │                                      │── compose_session_evaluation_prompt ─>│
   │                                      │<── session_evaluation JSON ──────────│
   │<── { id, status: draft, eval } ─────│                                      │
   │                                      │                                      │
   │── GET /sessions/{id}/preview ──────>│                                      │
   │<── { session_evaluation } ──────────│                                      │
   │                                      │                                      │
   │   (user reviews / edits segments)    │                                      │
   │                                      │                                      │
   │── PUT /sessions/{id}/evaluation ───>│                                      │
   │<── { updated eval } ───────────────│                                      │
   │                                      │                                      │
   │── POST /sessions/{id}/start ──────>│                                      │
   │                                      │── generate segment 1 content_script ─>│
   │                                      │<── content_script (with markers) ────│
   │<── { status: in_progress, segs } ──│                                      │
   │                                      │                                      │
   │── GET /segments/1/stream ─────────>│                                      │
   │                                      │── asyncio.create_task(prefetch seg 2)│
   │                                      │         background ──── generate ──>│
   │<── data: {segment_start} ──────────│         task             seg 2       │
   │<── data: {emotion: warm} ──────────│           │           content         │
   │<── data: {text: "Hey there!"} ─────│           │              │            │
   │<── data: {pause: 400} ─────────────│           │              │            │
   │<── data: {text: "Welcome..."} ─────│           │<─── done ───│            │
   │<── data: {whiteboard: ...} ────────│           │                           │
   │<── data: {segment_end, order:1} ───│           │ write seg 2               │
   │                                      │           │ content_script            │
   │   (frontend: close EventSource)      │           │ to DB                     │
   │   (frontend: show "next" button)     │                                      │
   │                                      │                                      │
   │── GET /segments/2/stream ─────────>│                                      │
   │                                      │── content ready? yes → stream       │
   │                                      │── asyncio.create_task(prefetch seg 3)│
   │<── data: {segment_start} ──────────│                                      │
   │<── ... events ... ─────────────────│                                      │
   │<── data: {segment_end, order:2} ───│                                      │
   │                                      │                                      │
   │   ... repeat for each segment ...    │                                      │
   │                                      │                                      │
   │── GET /segments/N/stream ─────────>│  (last segment)                      │
   │<── data: {segment_end, order:N} ───│                                      │
   │<── data: {session_end} ────────────│                                      │
   │                                      │                                      │
   │── POST /sessions/{id}/end ────────>│                                      │
   │                                      │── generate goodbye message ─────────>│
   │<── { goodbye_message, 100% } ──────│<── goodbye text ─────────────────────│
```

---

## 19. Backend vs Frontend Responsibilities

### Backend owns:
| Responsibility | Details |
|----------------|---------|
| Session lifecycle management | Create, start, pause, resume, end, cancel |
| AI content generation | Segment planning, content_script generation, goodbye messages |
| WPM-calibrated content length | `calculate_target_wpm(personality, mood)` × `duration_seconds / 60` |
| N+1 prefetch orchestration | Background `asyncio.Task` for next segment |
| Content readiness wait logic | Polling DB with exponential backoff |
| Config invalidation | Nulling pending segment content when config changes |
| Script tokenization + chunk numbering | Parsing `content_script` into structured SSE events with `chunk` field |
| Pulse metric storage | Persisting focus levels, activity-based adjustments |
| Live doubt streaming | Sentence-buffered streaming answer with segment context |
| Auth | JWT verification for both headers and query params |

### Frontend owns:
| Responsibility | Details |
|----------------|---------|
| TTS audio playback | Web Speech API with `useAudioQueue` hook, rate calibration, emotion delta |
| Emotion → voice mapping | Translating `emotion` events into ElevenLabs `voice_settings` |
| Pause timing | Inserting silence between TTS calls based on `pause` duration |
| Whiteboard rendering | Drawing diagrams, equations, animations from `whiteboard` events |
| Segment switching | Deciding when to connect to the next segment's SSE endpoint |
| **Buffer-replay** | Buffering all SSE events locally; replaying from saved index on resume (no backend re-hit) |
| Pulse UI | Displaying engagement meter, triggering `adjust`/`record` calls |
| Session progress UI | Showing current segment, progress bar, time remaining |
| EventSource / fetch management | Opening, closing, error handling for SSE connections |
| Transcript display | Optionally showing live captions from `text` events |

### Neither (intentionally omitted):
| Feature | Why |
|---------|-----|
| Backend audio streaming | Frontend handles TTS directly with ElevenLabs |
| Backend segment auto-advance | Frontend controls pacing and transitions |
| Backend transcript storage | Content exists in `content_script`; no separate transcript table needed |
| Real-time collaboration | Single-user sessions by design |
