"""
Speech Script Processor — converts LLM text output into speech-optimized scripts
with pause markers, emotional cues, and rhythm control for TTS delivery.

This processor sits between the LLM response and the TTS engine, enriching
plain text with vocal cues that make the tutor sound human.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CALM = "calm"
    ENCOURAGING = "encouraging"
    CONCERNED = "concerned"
    CURIOUS = "curious"
    WARM = "warm"
    SERIOUS = "serious"


class SegmentEnergy(str, Enum):
    HIGH = "high"          # introductions, celebrations, curiosity triggers
    MEDIUM = "medium"      # core teaching, examples
    LOW = "low"            # recap, summary, reflective moments
    BUILDING = "building"  # gradually increasing energy (story arcs)


# ── Pause durations (ms) ───────────────────────────────────────────────

PAUSE_MICRO = 200       # natural breath between clauses
PAUSE_SHORT = 400       # between sentences
PAUSE_MEDIUM = 700      # between ideas / after a question
PAUSE_LONG = 1200       # between segments / for dramatic effect
PAUSE_THINKING = 1500   # "let that sink in" moments


# ── Voice dynamics per emotion ─────────────────────────────────────────

EMOTION_VOICE_PARAMS: dict[Emotion, dict] = {
    Emotion.NEUTRAL: {"stability": 0.50, "similarity_boost": 0.75, "style": 0.40, "speed": 1.0},
    Emotion.EXCITED: {"stability": 0.35, "similarity_boost": 0.80, "style": 0.70, "speed": 1.10},
    Emotion.CALM: {"stability": 0.70, "similarity_boost": 0.75, "style": 0.30, "speed": 0.92},
    Emotion.ENCOURAGING: {"stability": 0.45, "similarity_boost": 0.80, "style": 0.60, "speed": 1.05},
    Emotion.CONCERNED: {"stability": 0.60, "similarity_boost": 0.70, "style": 0.35, "speed": 0.95},
    Emotion.CURIOUS: {"stability": 0.40, "similarity_boost": 0.78, "style": 0.55, "speed": 1.02},
    Emotion.WARM: {"stability": 0.55, "similarity_boost": 0.80, "style": 0.50, "speed": 0.97},
    Emotion.SERIOUS: {"stability": 0.65, "similarity_boost": 0.70, "style": 0.25, "speed": 0.93},
}


# ── Energy → voice base adjustments ───────────────────────────────────

ENERGY_ADJUSTMENTS: dict[SegmentEnergy, dict] = {
    SegmentEnergy.HIGH: {"stability_delta": -0.08, "style_delta": +0.10, "speed_delta": +0.05},
    SegmentEnergy.MEDIUM: {"stability_delta": 0.0, "style_delta": 0.0, "speed_delta": 0.0},
    SegmentEnergy.LOW: {"stability_delta": +0.10, "style_delta": -0.08, "speed_delta": -0.05},
    SegmentEnergy.BUILDING: {"stability_delta": -0.04, "style_delta": +0.05, "speed_delta": +0.02},
}


@dataclass
class SpeechChunk:
    """A single chunk of speech-ready text with delivery metadata."""
    text: str
    emotion: Emotion = Emotion.NEUTRAL
    pause_after_ms: int = PAUSE_SHORT
    voice_params: dict = field(default_factory=dict)


@dataclass
class SpeechScript:
    """Full speech script: an ordered list of chunks with global metadata."""
    chunks: list[SpeechChunk] = field(default_factory=list)
    segment_energy: SegmentEnergy = SegmentEnergy.MEDIUM
    personality: str = "very_friendly"

    @property
    def full_text(self) -> str:
        """Reconstruct marked-up text for debugging / logging."""
        parts = []
        for chunk in self.chunks:
            if chunk.emotion != Emotion.NEUTRAL:
                parts.append(f"[{chunk.emotion.value}]")
            parts.append(chunk.text)
            if chunk.pause_after_ms > PAUSE_SHORT:
                parts.append(f"<pause:{chunk.pause_after_ms}ms>")
        return " ".join(parts)

    @property
    def plain_text(self) -> str:
        """Text without any markers, for plain TTS fallback."""
        return " ".join(c.text for c in self.chunks)

    def to_tts_segments(self) -> list[dict]:
        """Convert to a list of TTS-ready dicts for the voice service."""
        segments = []
        for chunk in self.chunks:
            params = compute_voice_params(
                emotion=chunk.emotion,
                energy=self.segment_energy,
                personality=self.personality,
            )
            segments.append({
                "text": chunk.text,
                "voice_settings": params,
                "pause_after_ms": chunk.pause_after_ms,
            })
        return segments


# ── Personality → base voice profile ──────────────────────────────────

PERSONALITY_VOICE_PROFILES: dict[str, dict] = {
    "strict": {
        "stability": 0.65,
        "similarity_boost": 0.70,
        "style": 0.25,
        "speed": 0.95,
        "use_speaker_boost": True,
    },
    "very_friendly": {
        "stability": 0.45,
        "similarity_boost": 0.80,
        "style": 0.55,
        "speed": 1.0,
        "use_speaker_boost": True,
    },
    "attentive": {
        "stability": 0.55,
        "similarity_boost": 0.75,
        "style": 0.40,
        "speed": 0.97,
        "use_speaker_boost": True,
    },
    "funny": {
        "stability": 0.35,
        "similarity_boost": 0.80,
        "style": 0.70,
        "speed": 1.05,
        "use_speaker_boost": True,
    },
    "motivational": {
        "stability": 0.40,
        "similarity_boost": 0.85,
        "style": 0.65,
        "speed": 1.03,
        "use_speaker_boost": True,
    },
    "patient": {
        "stability": 0.60,
        "similarity_boost": 0.75,
        "style": 0.35,
        "speed": 0.90,
        "use_speaker_boost": True,
    },
    "storyteller": {
        "stability": 0.38,
        "similarity_boost": 0.82,
        "style": 0.68,
        "speed": 0.98,
        "use_speaker_boost": True,
    },
}

DEFAULT_VOICE_PROFILE = PERSONALITY_VOICE_PROFILES["very_friendly"]


# ── Segment type → energy mapping ─────────────────────────────────────

SEGMENT_TYPE_ENERGY: dict[str, SegmentEnergy] = {
    "introduction": SegmentEnergy.HIGH,
    "core_teaching": SegmentEnergy.MEDIUM,
    "example": SegmentEnergy.MEDIUM,
    "analogy": SegmentEnergy.BUILDING,
    "whiteboard": SegmentEnergy.LOW,
    "animation_demo": SegmentEnergy.BUILDING,
    "practice": SegmentEnergy.MEDIUM,
    "qa_check": SegmentEnergy.HIGH,
    "story": SegmentEnergy.BUILDING,
    "curiosity_trigger": SegmentEnergy.HIGH,
    "recap": SegmentEnergy.LOW,
    "summary": SegmentEnergy.LOW,
}


# ── Mood → speed modifier ────────────────────────────────────────────

MOOD_SPEED_MODIFIER: dict[str, float] = {
    "very_focused": 1.05,    # student is engaged, can handle faster
    "focused": 1.0,
    "light": 0.98,
    "non_attentive": 0.95,   # slow down to re-engage
    "tired": 0.88,           # slower for tired students
    "curious": 1.0,
    "exam_prep": 1.02,
}


def compute_voice_params(
    *,
    emotion: Emotion = Emotion.NEUTRAL,
    energy: SegmentEnergy = SegmentEnergy.MEDIUM,
    personality: str = "very_friendly",
    mood: str = "focused",
) -> dict:
    """
    Compute final ElevenLabs voice_settings by layering:
    1. Personality base profile
    2. Emotion adjustments
    3. Energy adjustments
    4. Mood speed modifier

    All values are clamped to [0, 1] (speed to [0.7, 1.3]).
    """
    # Start from personality base
    base = PERSONALITY_VOICE_PROFILES.get(personality, DEFAULT_VOICE_PROFILE).copy()

    # Layer emotion
    emo_params = EMOTION_VOICE_PARAMS.get(emotion, EMOTION_VOICE_PARAMS[Emotion.NEUTRAL])
    # Blend: 60% personality base, 40% emotion influence
    base["stability"] = base["stability"] * 0.6 + emo_params["stability"] * 0.4
    base["style"] = base["style"] * 0.6 + emo_params["style"] * 0.4
    base["speed"] = base["speed"] * 0.6 + emo_params["speed"] * 0.4

    # Layer energy
    energy_adj = ENERGY_ADJUSTMENTS.get(energy, ENERGY_ADJUSTMENTS[SegmentEnergy.MEDIUM])
    base["stability"] += energy_adj["stability_delta"]
    base["style"] += energy_adj["style_delta"]
    base["speed"] += energy_adj["speed_delta"]

    # Layer mood speed
    mood_mod = MOOD_SPEED_MODIFIER.get(mood, 1.0)
    base["speed"] *= mood_mod

    # Clamp
    base["stability"] = max(0.0, min(1.0, base["stability"]))
    base["similarity_boost"] = max(0.0, min(1.0, base["similarity_boost"]))
    base["style"] = max(0.0, min(1.0, base["style"]))
    base["speed"] = max(0.7, min(1.3, base["speed"]))

    return {
        "stability": round(base["stability"], 3),
        "similarity_boost": round(base["similarity_boost"], 3),
        "style": round(base["style"], 3),
        "speed": round(base["speed"], 3),
        "use_speaker_boost": base.get("use_speaker_boost", True),
    }


# ── Pattern matchers for parsing LLM speech output ───────────────────

_EMOTION_RE = re.compile(r"\[(\w+)\]")
_PAUSE_RE = re.compile(r"<pause:(\d+)ms>")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def parse_speech_text(
    raw_text: str,
    *,
    personality: str = "very_friendly",
    segment_type: str = "core_teaching",
    mood: str = "focused",
) -> SpeechScript:
    """
    Parse LLM output containing emotion markers and pause tags
    into a structured SpeechScript.

    Expected markers in raw_text:
      [excited] This is amazing!
      <pause:700ms>
      [calm] Now let's think about this carefully.
    """
    energy = SEGMENT_TYPE_ENERGY.get(segment_type, SegmentEnergy.MEDIUM)
    script = SpeechScript(personality=personality, segment_energy=energy)

    current_emotion = Emotion.NEUTRAL
    # Split into lines for processing
    lines = raw_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for emotion markers
        emotion_match = _EMOTION_RE.match(line)
        if emotion_match:
            emotion_name = emotion_match.group(1).lower()
            try:
                current_emotion = Emotion(emotion_name)
            except ValueError:
                pass
            # Remove the marker from text
            line = _EMOTION_RE.sub("", line, count=1).strip()
            if not line:
                continue

        # Check for inline pauses and split around them
        parts = _PAUSE_RE.split(line)
        pause_matches = _PAUSE_RE.findall(line)

        text_parts = parts[::2]   # text between pauses
        pause_values = [int(p) for p in pause_matches]

        for i, text_part in enumerate(text_parts):
            text_part = text_part.strip()
            if not text_part:
                continue

            # Split long text into sentence-level chunks
            sentences = _SENTENCE_SPLIT_RE.split(text_part)
            for j, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Determine pause: use explicit pause if present, else default
                if i < len(pause_values):
                    pause = pause_values[i]
                elif j < len(sentences) - 1:
                    pause = PAUSE_SHORT
                else:
                    pause = PAUSE_MEDIUM

                script.chunks.append(SpeechChunk(
                    text=sentence,
                    emotion=current_emotion,
                    pause_after_ms=pause,
                ))

    # Add segment-end pause
    if script.chunks:
        script.chunks[-1].pause_after_ms = PAUSE_LONG

    return script


def enrich_for_speech(
    text: str,
    *,
    personality: str = "very_friendly",
    segment_type: str = "core_teaching",
    mood: str = "focused",
) -> dict:
    """
    High-level helper: parse raw text and return a dict with:
    - tts_segments: list of {text, voice_settings, pause_after_ms}
    - plain_text: plain text fallback
    - full_marked_text: text with markers for debugging
    """
    script = parse_speech_text(
        text,
        personality=personality,
        segment_type=segment_type,
        mood=mood,
    )
    return {
        "tts_segments": script.to_tts_segments(),
        "plain_text": script.plain_text,
        "full_marked_text": script.full_text,
    }
