"""Patch SESSION_STREAMING_README.md: update sections 9, 15, 16, 19 and add future scalability section."""
import re

FILE = "SESSION_STREAMING_README.md"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# ── Replace Section 9: Pause & Resume ───────────────────────────────────
old_9_start = "## 9. Pause & Resume with Chunk Tracking"
old_9_end = "\n---\n\n## 10."
s9_start = content.find(old_9_start)
s9_end = content.find(old_9_end, s9_start)
assert s9_start != -1 and s9_end != -1, f"Section 9 not found: {s9_start}, {s9_end}"

NEW_SECTION_9 = """## 9. Pause & Resume — Client-Side Buffer Replay

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
"""

content = content[:s9_start] + NEW_SECTION_9 + content[s9_end:]

# ── Replace Section 15: Frontend TTS Integration ───────────────────────
old_15_start = "## 15. Frontend TTS Integration (ElevenLabs)"
old_15_end = "\n---\n\n## 16."
s15_start = content.find(old_15_start)
s15_end = content.find(old_15_end, s15_start)
assert s15_start != -1 and s15_end != -1, f"Section 15 not found: {s15_start}, {s15_end}"

NEW_SECTION_15 = """## 15. Frontend TTS Integration (Web Speech API)

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
"""

content = content[:s15_start] + NEW_SECTION_15 + content[s15_end:]

# ── Replace Section 16: Frontend Whiteboard Rendering ──────────────────
old_16_start = "## 16. Frontend Whiteboard Rendering"
old_16_end = "\n---\n\n## 17."
s16_start = content.find(old_16_start)
s16_end = content.find(old_16_end, s16_start)
assert s16_start != -1 and s16_end != -1, f"Section 16 not found: {s16_start}, {s16_end}"

NEW_SECTION_16 = """## 16. Frontend Whiteboard Rendering

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
- **Equation:** Contains math characters (`=`, `^`, `\\frac`, `\\sqrt`, etc.)
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
"""

content = content[:s16_start] + NEW_SECTION_16 + content[s16_end:]

# ── Update Section 19: Backend vs Frontend table ──────────────────────
# Replace the "Chunk tracking" row and "TTS audio playback" row
content = content.replace(
    "| **Chunk tracking** | Storing `lastChunk` on every event; passing `from_chunk` on resume |",
    "| **Buffer-replay** | Buffering all SSE events locally; replaying from saved index on resume (no backend re-hit) |"
)
content = content.replace(
    "| TTS audio playback | ElevenLabs SDK integration, voice selection, audio queue |",
    "| TTS audio playback | Web Speech API with `useAudioQueue` hook, rate calibration, emotion delta |"
)
content = content.replace(
    "| Emotion \xe2\x86\x92 voice mapping | Translating `emotion` events into ElevenLabs `voice_settings` |",
    "| Emotion \xe2\x86\x92 voice mapping | Translating `emotion` events into pitch + rate delta adjustments |"
)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("README patched successfully!")
