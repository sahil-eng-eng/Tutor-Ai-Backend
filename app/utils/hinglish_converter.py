"""
Hinglish converter — batch-converts English text to Hinglish (Hindi in Roman script).

Used when ``session.language == "hinglish"``: the content_script is generated in
English, then all speakable texts are converted to Hinglish in a single LLM call.
The resulting mapping is passed to the SSE parser so each event carries both
an English ``readable_text`` and a ``hinglish`` key for TTS.
"""

import json
import logging
from typing import Optional

from app.services.ai_tutor_service import generate_json_response

logger = logging.getLogger("ai_tutor")


# ---------------------------------------------------------------------------
# Extraction — mirrors the readable_text values emitted by script_parser.py
# ---------------------------------------------------------------------------

def extract_speakable_texts(content_script: str) -> list[str]:
    """Extract all texts that will be spoken by TTS from a structured JSON content_script.

    The returned texts correspond *exactly* to the ``readable_text`` values
    emitted by ``_parse_json_blocks`` so that the mapping keys match at lookup time.
    """
    texts: list[str] = []
    try:
        data = json.loads(content_script)
        if not isinstance(data, dict) or "blocks" not in data:
            return texts
    except (json.JSONDecodeError, ValueError, TypeError):
        return texts

    for block in data.get("blocks", []):
        for section in block.get("sections", []):
            heading = section.get("heading", "").strip()
            if heading:
                # section_start → readable_text = heading
                texts.append(heading)

            for element in section.get("elements", []):
                etype = element.get("type", "")

                if etype == "text":
                    content = (element.get("value") or element.get("content") or "").strip()
                    if content:
                        # text → readable_text = content
                        texts.append(content)

                elif etype == "list":
                    for item in element.get("items", []):
                        item_text = str(item).strip()
                        if item_text:
                            # list_item → readable_text = item_text
                            texts.append(item_text)

                elif etype == "question":
                    q_text = (element.get("question") or "").strip()
                    q_opts = element.get("options", [])
                    if q_text:
                        opts_readable = ". ".join(
                            f"Option {i + 1}: {opt}" for i, opt in enumerate(q_opts)
                        )
                        readable = f"Here is a question. {q_text} {opts_readable}."
                        # question → readable_text = readable
                        texts.append(readable)

    return texts


# ---------------------------------------------------------------------------
# Conversion — single LLM call for the whole batch
# ---------------------------------------------------------------------------

async def convert_texts_to_hinglish(
    texts: list[str],
    model: str = "gpt-4o-mini",
) -> dict[str, str]:
    """Convert a list of English texts to Hinglish via a single LLM call.

    Returns a mapping ``{english_text: hinglish_text}``.
    On failure, returns a passthrough mapping (original text → original text).
    """
    if not texts:
        return {}

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_texts: list[str] = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)

    # Build numbered list for the LLM
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(unique_texts))

    system_prompt = (
        "You are a language converter. Convert the given English texts to Hinglish "
        "(Hindi language written in Roman/Latin script, commonly used in casual Indian conversation). "
        "Rules:\n"
        "- Keep technical terms, proper nouns, numbers, and formulas in English\n"
        "- Use natural Hinglish as spoken in everyday Indian conversation\n"
        "- Maintain the same meaning, tone, and structure\n"
        "- Return a JSON object with a single key 'translations' containing an array of strings\n"
        "- The array must have exactly the same number of items as the input\n"
        "- Each item in the array is the Hinglish version of the corresponding input text\n"
    )

    user_message = f"Convert these {len(unique_texts)} English texts to Hinglish:\n\n{numbered}"

    try:
        result = await generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            temperature=0.3,
            max_tokens=8192,
        )

        translations = result.get("translations", []) if isinstance(result, dict) else []

        mapping: dict[str, str] = {}
        for i, orig in enumerate(unique_texts):
            if i < len(translations):
                mapping[orig] = str(translations[i])
            else:
                mapping[orig] = orig  # fallback to original

        return mapping

    except Exception:
        logger.exception("Hinglish conversion failed, falling back to original texts")
        return {t: t for t in unique_texts}


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

async def get_hinglish_map(
    content_script: str,
    model: str = "gpt-4o-mini",
) -> dict[str, str]:
    """Extract speakable texts from *content_script* and convert them to Hinglish.

    Returns a mapping ``{english_readable_text: hinglish_text}`` suitable for
    passing to ``parse_script_to_sse_events(hinglish_map=…)``.
    """
    texts = extract_speakable_texts(content_script)
    if not texts:
        return {}
    return await convert_texts_to_hinglish(texts, model=model)
