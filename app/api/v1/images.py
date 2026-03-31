"""
Image callback endpoint — receives POST from nano-banana when an image
generation task completes. Resolves the pending asyncio.Future so the
image_generation_service can continue processing.

This endpoint is intentionally unauthenticated because nano-banana is
the caller and it only knows the callback URL — not our JWT tokens.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.image_generation_service import resolve_callback

logger = logging.getLogger("ai_tutor")

router = APIRouter()


@router.post("/callback")
async def image_callback(request: Request) -> JSONResponse:
    """Nano-banana POSTs here when image generation is done.

    Expected payload::

        {
            "msg": "...",
            "code": 200,
            "data": {
                "taskId": "abc123",
                "info": {
                    "resultImageUrl": "https://..."
                }
            }
        }
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Image callback received non-JSON body")
        return JSONResponse({"status": "error", "detail": "invalid JSON"}, status_code=400)

    code = body.get("code")
    data = body.get("data") or {}
    task_id = data.get("taskId")
    info = data.get("info") or {}
    image_url = info.get("resultImageUrl")

    if not task_id:
        logger.warning("Image callback missing taskId: %s", body)
        return JSONResponse({"status": "error", "detail": "missing taskId"}, status_code=400)

    if code != 200 or not image_url:
        logger.warning("Image callback indicates failure — taskId=%s code=%s", task_id, code)
        return JSONResponse({"status": "error", "detail": "generation failed"}, status_code=200)

    resolved = resolve_callback(task_id, image_url)
    if resolved:
        logger.info("Image callback resolved: taskId=%s", task_id)
    else:
        logger.warning("Image callback for unknown/stale taskId=%s", task_id)

    return JSONResponse({"status": "ok"}, status_code=200)
