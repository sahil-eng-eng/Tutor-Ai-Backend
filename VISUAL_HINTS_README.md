# Visual Hints — Image Generation Pipeline

## Overview

The AI Tutor generates educational diagrams for every teaching block using the
**nano-banana** image generation API. Images appear in real-time during the
teaching session, synchronized wiVth the content being taught.

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ Session starts → content_script generated (blocks with visual_hints) │
│                  ↓                                                   │
│   fire_image_generation() — background task                          │
│       │                                                              │
│       ├─ For each visual_hint (sequential, block order):             │
│       │   1. POST to nano-banana with callBackUrl                    │
│       │      → immediate response: { taskId }                       │
│       │   2. Register asyncio.Future keyed by taskId                 │
│       │   3. Await Future (up to NANOBANANA_TIMEOUT_SECONDS)         │
│       │               ↓                                              │
│       │   nano-banana generates image asynchronously                 │
│       │               ↓                                              │
│       │   4. nano-banana POSTs to /api/v1/images/callback            │
│       │      → { taskId, info: { resultImageUrl } }                  │
│       │   5. Callback endpoint resolves the Future                   │
│       │   6. Image URL written to content_script + persisted to DB   │
│       │   7. (block_id, image_url) pushed to image_ready_queue       │
│       │                                                              │
│   Meanwhile, SSE streaming is sending teaching content:              │
│       │   - visual_hint events sent with image_url: null initially   │
│       │   - After each SSE event, queue is drained                   │
│       │   - image_ready events yielded to frontend                   │
│       │                                                              │
│   Frontend receives image_ready → updates block's imageUrl           │
│   BlockImagePanel: shimmer → actual image                            │
└────────────────────────────────────────────────────────────────────┘
```

## Configuration

Set these environment variables (`.env`):

| Variable | Description | Example |
|---|---|---|
| `NANOBANANA_API_URL` | Nano-banana generation endpoint | `https://api.nanobananaapi.ai/api/v1/nanobanana/generate` |
| `NANOBANANA_API_KEY` | Bearer token for authentication | `ea2b028d7edf04f1e35e99cf6f44928b` |
| `NANOBANANA_TIMEOUT_SECONDS` | Max seconds to wait for each callback | `60` |
| `NANOBANANA_CALLBACK_BASE_URL` | Your server's public URL (ngrok for dev) | `https://your-url.ngrok-free.dev` |
| `NANOBANANA_ENABLED` | Toggle image generation on/off | `true` |

The callback URL constructed is: `{NANOBANANA_CALLBACK_BASE_URL}/api/v1/images/callback`

## Files Modified / Created

### Backend

| File | Change |
|---|---|
| `app/services/image_generation_service.py` | **Rewritten** — callback pattern with asyncio.Future, pending task registry, `resolve_callback()`, queue-based image delivery |
| `app/api/v1/images.py` | **New** — `POST /api/v1/images/callback` endpoint for nano-banana |
| `app/api/v1/router.py` | Added images router at `/images` prefix |
| `app/services/session_service.py` | Queue-based `image_ready` SSE event interleaving during streaming |
| `app/config.py` | Added `NANOBANANA_CALLBACK_BASE_URL`, updated default API URL + timeout |
| `app/prompts/base_prompts.py` | Visual hints now mandatory per block with detailed image-gen prompt guidance |

### Frontend

| File | Change |
|---|---|
| `src/components/WhiteboardCanvas.tsx` | Fixed active block content scroll (added `flex flex-col` to parent) |
| `src/pages/ActiveSession.tsx` | Fixed page layout scroll — `shrink-0` on timeline/controls, `min-h-0` on canvas |

## Nano-Banana API Contract

**Request** — `POST https://api.nanobananaapi.ai/api/v1/nanobanana/generate`

```json
{
  "prompt": "A billiard table viewed from above showing momentum conservation...",
  "type": "TEXTTOIAMGE",
  "numImages": 1,
  "image_size": "16:9",
  "callBackUrl": "https://your-server/api/v1/images/callback"
}
```

**Immediate Response:**
```json
{
  "code": 200,
  "msg": "success",
  "data": { "taskId": "abc123..." }
}
```

**Callback POST** (later, to your callBackUrl):
```json
{
  "msg": "...",
  "code": 200,
  "data": {
    "taskId": "abc123...",
    "info": {
      "resultImageUrl": "https://cdn.nanobanana.../image.jpg"
    }
  }
}
```

## Frontend Image Display

1. **Visual hint arrives** (SSE `visual_hint` event) → `image_url: null` → shimmer animation shown
2. **Image callback resolved** → SSE `image_ready` event → `image_url` updated
3. **BlockImagePanel** transitions from shimmer to actual image with smooth animation
4. **Click image** → full-screen lightbox overlay
5. **Completed blocks** show image thumbnails in sidebar accordion + reference tree

## Scrolling Fix

The Active Session page scroll issue was caused by:
- Missing `flex flex-col` on the BlockContentRenderer wrapper div (preventing `overflow-y-auto` from working)
- Missing `shrink-0` on timeline and controls (causing them to be compressed/hidden)
- Non-standard `h-[-webkit-fill-available]` replaced with `min-h-0` for proper flex behavior
