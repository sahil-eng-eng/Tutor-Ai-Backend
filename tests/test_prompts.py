"""Tests for the prompt composition system."""

import pytest

from app.prompts.prompt_composer import (
    compose_system_prompt,
    compose_doubt_resolution_prompt,
    compose_mcq_generation_prompt,
    compose_segment_plan_prompt,
    compose_notes_generation_prompt,
)
from app.prompts.interaction_prompts import get_random_response, CELEBRATION_RESPONSES


class TestPromptComposer:
    def test_compose_system_prompt_basic(self):
        prompt = compose_system_prompt(
            tutor_name="Alex",
            language="English",
            concept_name="Algebra",
            study_level="intermediate",
            entire_session_type="intermediate",
            personality="very_friendly",
            mood="focused",
            user_type="college_student",
            duration_minutes=30,
        )
        assert "Alex" in prompt
        assert len(prompt) > 100

    def test_compose_system_prompt_all_levels(self):
        for level in ("beginner", "basic", "intermediate", "advanced", "expert"):
            prompt = compose_system_prompt(
                tutor_name="Tutor",
                language="English",
                concept_name="Physics",
                study_level=level,
                entire_session_type="intermediate",
                personality="patient",
                mood="focused",
                user_type="school_student",
                duration_minutes=45,
            )
            assert len(prompt) > 50

    def test_compose_system_prompt_all_personalities(self):
        for p in (
            "strict",
            "very_friendly",
            "attentive",
            "funny",
            "motivational",
            "patient",
            "storyteller",
        ):
            prompt = compose_system_prompt(
                tutor_name="T",
                language="English",
                concept_name="Chemistry",
                study_level="basic",
                entire_session_type="intermediate",
                personality=p,
                mood="focused",
                user_type="college_student",
                duration_minutes=30,
            )
            assert len(prompt) > 50

    def test_compose_doubt_resolution_prompt(self):
        prompt = compose_doubt_resolution_prompt(
            doubt_text="What is the chain rule?",
            study_level="intermediate",
            current_topic="Derivatives",
        )
        assert "chain rule" in prompt.lower()

    def test_compose_mcq_generation_prompt(self):
        prompt = compose_mcq_generation_prompt(
            topic="Photosynthesis",
            study_level="basic",
            count=3,
        )
        assert "3" in prompt
        assert "Photosynthesis" in prompt

    def test_compose_segment_plan_prompt(self):
        prompt = compose_segment_plan_prompt(
            concept_name="World War II",
            description=None,
            study_level="intermediate",
            session_type="learn_new_concept",
            duration_minutes=60,
        )
        assert "World War II" in prompt

    def test_compose_notes_generation_prompt(self):
        prompt = compose_notes_generation_prompt(
            concept_name="Organic Chemistry",
            segments_content="Covered benzene rings and alkanes",
        )
        assert "Organic Chemistry" in prompt


class TestInteractionPrompts:
    def test_random_response_returns_string(self):
        result = get_random_response(CELEBRATION_RESPONSES)
        assert isinstance(result, str)
        assert len(result) > 0
        assert result in CELEBRATION_RESPONSES

    def test_random_response_from_all_arrays(self):
        from app.prompts.interaction_prompts import (
            DOUBT_ACKNOWLEDGEMENT_RESPONSES,
            PULSE_LOW_RESPONSES,
            SEGMENT_TRANSITION_RESPONSES,
            CURIOSITY_TRIGGERS,
        )
        for arr in (
            DOUBT_ACKNOWLEDGEMENT_RESPONSES,
            PULSE_LOW_RESPONSES,
            SEGMENT_TRANSITION_RESPONSES,
            CURIOSITY_TRIGGERS,
        ):
            result = get_random_response(arr)
            assert result in arr
