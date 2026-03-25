"""
Whiteboard Engine — generates structured whiteboard instructions synced with speech.

Zero-cost approach: produces JSON instruction sets that the frontend renders
on a canvas/whiteboard surface. No image generation or external services needed.

Whiteboard instruction types:
  - write_text: Display text at a position
  - write_formula: Display a math formula (KaTeX/LaTeX format)
  - draw_diagram: Structured diagram specification (nodes + edges)
  - draw_shape: Basic shape drawing (rect, circle, arrow, line)
  - highlight: Highlight a region or text
  - clear: Clear all or part of the board
  - step: Step-by-step reveal (numbered list items)
  - code_block: Display code with syntax highlighting
  - table: Display a structured table
  - image_placeholder: Placeholder for a concept image (with alt text)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger("ai_tutor")


# ── Whiteboard Instruction Builders ─────────────────────────────────────

def build_text_instruction(
    text: str,
    position: str = "center",
    style: str = "heading",
    color: str = "#333333",
) -> dict[str, Any]:
    return {
        "type": "write_text",
        "text": text,
        "position": position,
        "style": style,  # heading, subheading, body, emphasis, note
        "color": color,
    }


def build_formula_instruction(
    latex: str,
    label: Optional[str] = None,
    position: str = "center",
) -> dict[str, Any]:
    return {
        "type": "write_formula",
        "latex": latex,
        "label": label,
        "position": position,
    }


def build_diagram_instruction(
    title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    layout: str = "horizontal",
) -> dict[str, Any]:
    """Structured diagram as nodes + edges (rendered by frontend with D3/Canvas).

    nodes: [{"id": "n1", "label": "Start", "shape": "rect|circle|diamond"}]
    edges: [{"from": "n1", "to": "n2", "label": "next"}]
    """
    return {
        "type": "draw_diagram",
        "title": title,
        "nodes": nodes,
        "edges": edges,
        "layout": layout,  # horizontal, vertical, radial, tree
    }


def build_step_instruction(
    title: str,
    steps: list[str],
    reveal: str = "sequential",
) -> dict[str, Any]:
    return {
        "type": "step",
        "title": title,
        "steps": steps,
        "reveal": reveal,  # sequential, all_at_once
    }


def build_code_block_instruction(
    code: str,
    language: str = "python",
    highlight_lines: Optional[list[int]] = None,
) -> dict[str, Any]:
    return {
        "type": "code_block",
        "code": code,
        "language": language,
        "highlight_lines": highlight_lines or [],
    }


def build_table_instruction(
    title: str,
    headers: list[str],
    rows: list[list[str]],
) -> dict[str, Any]:
    return {
        "type": "table",
        "title": title,
        "headers": headers,
        "rows": rows,
    }


def build_clear_instruction(region: str = "all") -> dict[str, Any]:
    return {"type": "clear", "region": region}


# ── Parse Whiteboard Cues from Content Script ──────────────────────────

_WHITEBOARD_PATTERN = re.compile(
    r"\[WHITEBOARD:\s*(.*?)\]",
    re.IGNORECASE | re.DOTALL,
)


def parse_whiteboard_cues_from_script(content_script: str) -> list[dict[str, Any]]:
    """Extract whiteboard instructions from embedded cue markers in a teaching script.

    Markers look like: [WHITEBOARD: action=write, content="H₂O → H₂ + O₂"]
    Returns a list of structured whiteboard instructions.
    """
    instructions: list[dict[str, Any]] = []

    for match in _WHITEBOARD_PATTERN.finditer(content_script):
        raw = match.group(1).strip()
        cue = _parse_cue_params(raw)

        action = cue.get("action", "write").lower()
        content_text = cue.get("content", "")

        if action in ("write", "write_text"):
            instructions.append(build_text_instruction(
                text=content_text,
                style=cue.get("style", "heading"),
            ))
        elif action in ("formula", "write_formula", "equation"):
            instructions.append(build_formula_instruction(
                latex=content_text,
                label=cue.get("label"),
            ))
        elif action in ("diagram", "draw_diagram", "draw"):
            instructions.append(build_diagram_instruction(
                title=content_text,
                nodes=_auto_nodes_from_description(content_text),
                edges=[],
                layout=cue.get("layout", "horizontal"),
            ))
        elif action in ("steps", "step", "list"):
            steps = [s.strip() for s in content_text.split(";") if s.strip()]
            instructions.append(build_step_instruction(
                title=cue.get("title", "Steps"),
                steps=steps,
            ))
        elif action in ("code", "code_block"):
            instructions.append(build_code_block_instruction(
                code=content_text,
                language=cue.get("language", "python"),
            ))
        elif action in ("table",):
            instructions.append(build_table_instruction(
                title=cue.get("title", "Comparison"),
                headers=cue.get("headers", "").split(";"),
                rows=[r.split(";") for r in content_text.split("|")],
            ))
        elif action == "clear":
            instructions.append(build_clear_instruction())
        else:
            # Default: write as text
            instructions.append(build_text_instruction(text=content_text))

    return instructions


def _parse_cue_params(raw: str) -> dict[str, str]:
    """Parse 'key=value, key2=value2' from a cue string."""
    params: dict[str, str] = {}
    # Match key=value or key="quoted value"
    for m in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*?)"|([^,\]]+))', raw):
        key = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3).strip()
        params[key] = value
    return params


def _auto_nodes_from_description(description: str) -> list[dict[str, Any]]:
    """Create basic diagram nodes from a textual description.

    Simple heuristic: split by common connectors like →, ->, and, then.
    """
    separators = re.split(r"\s*(?:→|->|➜|then|and|,)\s*", description)
    nodes = []
    for i, part in enumerate(separators):
        if part.strip():
            nodes.append({
                "id": f"n{i+1}",
                "label": part.strip()[:50],
                "shape": "rect",
            })
    return nodes


# ── Generate Synchronized Whiteboard Timeline ─────────────────────────

def generate_whiteboard_timeline(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate a synchronized whiteboard timeline from session segments.

    Returns a list of timed whiteboard events:
    [
        {
            "timestamp_seconds": 0,
            "segment_order": 1,
            "instructions": [...list of whiteboard instructions...]
        },
        ...
    ]
    """
    timeline: list[dict[str, Any]] = []
    cumulative_seconds = 0

    for seg in segments:
        instructions = []

        # Parse from content_script if available
        script = seg.get("content_script", "")
        if script:
            instructions.extend(parse_whiteboard_cues_from_script(script))

        # Parse from whiteboard_cues JSON if available
        wb_cues = seg.get("whiteboard_cues")
        if wb_cues and isinstance(wb_cues, dict):
            if wb_cues.get("content"):
                instructions.append(build_text_instruction(
                    text=wb_cues["content"],
                    style=wb_cues.get("style", "heading"),
                ))
            if wb_cues.get("formula"):
                instructions.append(build_formula_instruction(
                    latex=wb_cues["formula"],
                ))

        # Add segment title as a heading instruction at start
        if instructions:
            instructions.insert(0, build_clear_instruction())

        timeline.append({
            "timestamp_seconds": cumulative_seconds,
            "segment_order": seg.get("segment_order", 0),
            "segment_title": seg.get("title", ""),
            "instructions": instructions,
        })

        cumulative_seconds += seg.get("duration_seconds", 0) or 0

    return timeline
