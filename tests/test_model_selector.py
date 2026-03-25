"""Tests for model selector service."""

import pytest

from app.services.model_selector_service import (
    select_model,
    get_model_for_doubt_resolution,
    get_model_for_mcq_generation,
)


class TestModelSelector:
    def test_select_model_beginner(self):
        model = select_model(
            study_level="beginner",
            session_type="learn_new_concept",
        )
        assert isinstance(model, str)
        assert len(model) > 0

    def test_select_model_expert(self):
        model = select_model(
            study_level="expert",
            session_type="exam_preparation",
        )
        assert isinstance(model, str)

    def test_select_model_all_levels(self):
        for level in ("beginner", "basic", "intermediate", "advanced", "expert"):
            model = select_model(study_level=level, session_type="learn_new_concept")
            assert model

    def test_select_model_all_types(self):
        for stype in (
            "learn_new_concept",
            "practice_problems",
            "revision",
            "exam_preparation",
            "doubt_clearing",
        ):
            model = select_model(study_level="intermediate", session_type=stype)
            assert model

    def test_doubt_resolution_model(self):
        model = get_model_for_doubt_resolution(study_level="intermediate")
        assert isinstance(model, str)

    def test_mcq_generation_model(self):
        model = get_model_for_mcq_generation()
        assert isinstance(model, str)
