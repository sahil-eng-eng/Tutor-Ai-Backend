"""Tests for the speech processor engine."""

import pytest

from app.services.speech_processor import (
    Emotion,
    SegmentEnergy,
    SpeechChunk,
    SpeechScript,
    compute_voice_params,
    enrich_for_speech,
    parse_speech_text,
    PERSONALITY_VOICE_PROFILES,
    EMOTION_VOICE_PARAMS,
    PAUSE_SHORT,
    PAUSE_MEDIUM,
    PAUSE_LONG,
)


class TestComputeVoiceParams:
    def test_default_params(self):
        params = compute_voice_params()
        assert 0 <= params["stability"] <= 1
        assert 0 <= params["similarity_boost"] <= 1
        assert 0 <= params["style"] <= 1
        assert 0.7 <= params["speed"] <= 1.3
        assert params["use_speaker_boost"] is True

    def test_all_personalities(self):
        for personality in PERSONALITY_VOICE_PROFILES:
            params = compute_voice_params(personality=personality)
            assert 0 <= params["stability"] <= 1
            assert 0 <= params["style"] <= 1
            assert 0.7 <= params["speed"] <= 1.3

    def test_strict_is_more_stable_than_funny(self):
        strict = compute_voice_params(personality="strict")
        funny = compute_voice_params(personality="funny")
        assert strict["stability"] > funny["stability"]

    def test_patient_is_slower_than_funny(self):
        patient = compute_voice_params(personality="patient")
        funny = compute_voice_params(personality="funny")
        assert patient["speed"] < funny["speed"]

    def test_tired_mood_slows_speed(self):
        normal = compute_voice_params(mood="focused")
        tired = compute_voice_params(mood="tired")
        assert tired["speed"] < normal["speed"]

    def test_unknown_personality_uses_default(self):
        params = compute_voice_params(personality="nonexistent")
        default = compute_voice_params(personality="very_friendly")
        assert params["stability"] == default["stability"]

    def test_values_are_clamped(self):
        params = compute_voice_params(
            personality="strict",
            emotion=Emotion.CALM,
            energy=SegmentEnergy.LOW,
            mood="tired",
        )
        assert 0 <= params["stability"] <= 1
        assert 0.7 <= params["speed"] <= 1.3


class TestParseSpeechText:
    def test_simple_text(self):
        script = parse_speech_text("Hello, welcome to class.")
        assert len(script.chunks) >= 1
        assert script.chunks[0].text == "Hello, welcome to class."

    def test_emotion_markers(self):
        text = "[excited] This is amazing! The concept is so cool."
        script = parse_speech_text(text)
        assert script.chunks[0].emotion == Emotion.EXCITED

    def test_pause_markers(self):
        text = "First part. <pause:700ms> Second part."
        script = parse_speech_text(text)
        assert len(script.chunks) >= 2

    def test_multiple_emotions(self):
        text = "[excited] Wow, great job!\n[calm] Now let me explain the next part."
        script = parse_speech_text(text)
        emotions = [c.emotion for c in script.chunks]
        assert Emotion.EXCITED in emotions
        assert Emotion.CALM in emotions

    def test_last_chunk_has_long_pause(self):
        script = parse_speech_text("Hello. Goodbye.")
        assert script.chunks[-1].pause_after_ms == PAUSE_LONG

    def test_empty_text(self):
        script = parse_speech_text("")
        assert len(script.chunks) == 0

    def test_plain_text_property(self):
        text = "[excited] Hello! [calm] Goodbye."
        script = parse_speech_text(text)
        plain = script.plain_text
        assert "[excited]" not in plain
        assert "Hello!" in plain


class TestEnrichForSpeech:
    def test_returns_expected_keys(self):
        result = enrich_for_speech("Hello class, welcome.")
        assert "tts_segments" in result
        assert "plain_text" in result
        assert "full_marked_text" in result

    def test_tts_segments_have_voice_settings(self):
        result = enrich_for_speech("Hello class.")
        for seg in result["tts_segments"]:
            assert "text" in seg
            assert "voice_settings" in seg
            assert "pause_after_ms" in seg
            vs = seg["voice_settings"]
            assert "stability" in vs
            assert "speed" in vs

    def test_personality_affects_output(self):
        strict = enrich_for_speech("Hello.", personality="strict")
        funny = enrich_for_speech("Hello.", personality="funny")
        s_stab = strict["tts_segments"][0]["voice_settings"]["stability"]
        f_stab = funny["tts_segments"][0]["voice_settings"]["stability"]
        assert s_stab != f_stab


class TestSpeechScript:
    def test_to_tts_segments(self):
        script = SpeechScript(
            chunks=[SpeechChunk(text="Hello", emotion=Emotion.WARM)],
            personality="motivational",
        )
        segments = script.to_tts_segments()
        assert len(segments) == 1
        assert segments[0]["text"] == "Hello"
        assert "stability" in segments[0]["voice_settings"]

    def test_full_text_includes_markers(self):
        script = SpeechScript(
            chunks=[
                SpeechChunk(text="Wow!", emotion=Emotion.EXCITED, pause_after_ms=700),
            ],
        )
        assert "[excited]" in script.full_text
