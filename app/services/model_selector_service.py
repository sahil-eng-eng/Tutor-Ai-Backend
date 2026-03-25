"""
Model Selector — picks the right OpenAI model based on session parameters.
Optimizes cost by using cheaper models for basic content.
"""

from __future__ import annotations

from app.config import settings


# Cost tiers
MODEL_TIERS = {
    "cheap": settings.OPENAI_CHEAP_MODEL,
    "standard": settings.OPENAI_DEFAULT_MODEL,
    "premium": settings.OPENAI_PREMIUM_MODEL,
}


def select_model(
    study_level: str,
    session_type: str,
    concept_complexity: str = "medium",
) -> str:
    """
    Select the most cost-effective model based on session requirements.

    Rules:
    - basic/beginner level + basic_overview/revision → cheap model
    - intermediate level + intermediate session → standard model
    - advanced/expert level + in_depth session → premium model
    - exam_focused always gets at least standard
    """
    # Score the requirement
    level_scores = {
        "beginner": 1,
        "basic": 1,
        "intermediate": 2,
        "advanced": 3,
        "expert": 3,
    }
    type_scores = {
        "basic_overview": 1,
        "revision": 1,
        "intermediate": 2,
        "exam_focused": 2,
        "in_depth": 3,
    }
    complexity_scores = {
        "low": 0,
        "medium": 1,
        "high": 2,
    }

    score = (
        level_scores.get(study_level, 2)
        + type_scores.get(session_type, 2)
        + complexity_scores.get(concept_complexity, 1)
    )

    if score <= 3:
        return MODEL_TIERS["cheap"]
    elif score <= 5:
        return MODEL_TIERS["standard"]
    else:
        return MODEL_TIERS["premium"]


def get_model_for_doubt_resolution(study_level: str) -> str:
    """Doubt resolution uses standard model — clarity matters."""
    if study_level in ("advanced", "expert"):
        return MODEL_TIERS["premium"]
    return MODEL_TIERS["standard"]


def get_model_for_mcq_generation() -> str:
    """MCQ generation can use the cheap model."""
    return MODEL_TIERS["cheap"]
