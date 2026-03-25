"""
Prompt Composer — dynamically assembles the full system prompt from templates
based on user session configuration, user profile, and context.
"""

from __future__ import annotations

from typing import Any, Optional

from app.prompts.base_prompts import (
    BASE_TUTOR_PROMPT,
    STUDENT_CONTEXT_PROMPT,
    AGE_INSTRUCTIONS,
    SESSION_STRUCTURE_PROMPT,
    SESSION_TYPE_INSTRUCTIONS,
    DURATION_PROMPT_TEMPLATE,
    DURATION_INSTRUCTIONS,
    VISUAL_SYNC_PROMPT,
    CURIOSITY_AND_STORIES_PROMPT,
    SPEECH_FIRST_PROMPT,
    TEACHING_RHYTHM_PROMPT,
)
from app.prompts.personality_prompts import PERSONALITY_PROMPTS, DEFAULT_PERSONALITY_PROMPT
from app.prompts.mood_prompts import MOOD_PROMPTS, DEFAULT_MOOD_PROMPT
from app.prompts.level_prompts import LEVEL_PROMPTS, DEFAULT_LEVEL_PROMPT


# ── WPM (Words Per Minute) Calculator ────────────────────────────────
# Used to derive the target word count per segment based on duration + personality/mood.
_SLOW_PERSONALITIES = {"very_friendly", "funny", "storyteller", "patient"}
_FAST_PERSONALITIES = {"strict", "motivational", "attentive"}
_SLOW_MOODS = {"tired", "light"}
_FAST_MOODS = {"focused", "very_focused", "exam_prep"}


def calculate_target_wpm(personality: str, mood: str) -> int:
    """Return the ideal spoken WPM for AI content generation.

    - Friendly / relaxed (tired, light)    → 120–140 WPM → returns 130
    - Focused / strict / attentive        → 160+ WPM  → returns 165
    - Default (intermediate configs)      → 140–160 WPM → returns 150
    """
    if personality in _SLOW_PERSONALITIES or mood in _SLOW_MOODS:
        return 130
    if personality in _FAST_PERSONALITIES or mood in _FAST_MOODS:
        return 165
    return 150


def _pick_age_category(user_type: str, age: Optional[int]) -> str:
    if age and age < 12:
        return "young_school"
    if age and age < 18:
        return "teen_school"
    if user_type in ("college_student", "competitive_exam"):
        return "college"
    if user_type == "working_professional":
        return "professional"
    if age and age >= 18:
        return "college"
    return "default"


def compose_system_prompt(
    *,
    tutor_name: str = "Arjun",
    language: str = "english",
    user_type: str = "self_learner",
    age: Optional[int] = None,
    grade: Optional[str] = None,
    institution: Optional[str] = None,
    board: Optional[str] = None,
    concept_name: str,
    description: Optional[str] = None,
    study_level: str = "intermediate",
    entire_session_type: str = "intermediate",
    mood: str = "focused",
    personality: str = "very_friendly",
    duration_type: str = "ai_determined",
    duration_minutes: Optional[int] = None,
    session_mode: str = "single_session",
    extra_context: Optional[str] = None,
    user_material_summary: Optional[str] = None,
) -> str:
    """Compose a full system prompt from all template layers."""

    parts: list[str] = []

    # 1. Base tutor identity
    parts.append(
        BASE_TUTOR_PROMPT.format(tutor_name=tutor_name, language=language)
    )

    # 1b. Speech-first writing rules (critical — placed early)
    parts.append(SPEECH_FIRST_PROMPT)

    # 2. Personality layer
    personality_prompt = PERSONALITY_PROMPTS.get(personality, DEFAULT_PERSONALITY_PROMPT)
    parts.append(personality_prompt)

    # 3. Student context
    age_cat = _pick_age_category(user_type, age)
    age_specific = AGE_INSTRUCTIONS.get(age_cat, AGE_INSTRUCTIONS["default"])
    parts.append(
        STUDENT_CONTEXT_PROMPT.format(
            user_type=user_type.replace("_", " ").title(),
            age=age or "Not specified",
            grade=grade or "Not specified",
            institution=institution or "Not specified",
            board=board or "Not specified",
            language=language,
            age_specific_instructions=age_specific,
        )
    )

    # 4. Mood layer
    mood_prompt = MOOD_PROMPTS.get(mood, DEFAULT_MOOD_PROMPT)
    parts.append(mood_prompt)

    # 5. Study level layer
    level_prompt = LEVEL_PROMPTS.get(study_level, DEFAULT_LEVEL_PROMPT)
    parts.append(level_prompt)

    # 6. Session structure
    session_type_instr = SESSION_TYPE_INSTRUCTIONS.get(
        entire_session_type, SESSION_TYPE_INSTRUCTIONS["intermediate"]
    )
    duration_info = (
        f"{duration_minutes} minutes (set by student)"
        if duration_type == "user_defined" and duration_minutes
        else "Determined by you based on topic complexity"
    )
    parts.append(
        SESSION_STRUCTURE_PROMPT.format(
            concept_name=concept_name,
            description=description or "No specific focus described",
            study_level=study_level,
            entire_session_type=entire_session_type,
            duration_info=duration_info,
            session_mode=session_mode,
            session_type_instructions=session_type_instr,
        )
    )

    # 7. Duration management
    dur_key = duration_type if duration_type in DURATION_INSTRUCTIONS else "ai_determined"
    dur_instr = DURATION_INSTRUCTIONS[dur_key].format(
        duration_minutes=duration_minutes or "N/A"
    )
    parts.append(DURATION_PROMPT_TEMPLATE.format(duration_instructions=dur_instr))

    # 8. Visual sync
    parts.append(VISUAL_SYNC_PROMPT)

    # 9. Teaching rhythm & energy
    parts.append(TEACHING_RHYTHM_PROMPT)

    # 10. Curiosity & stories
    parts.append(CURIOSITY_AND_STORIES_PROMPT)

    # 10. User material context
    if user_material_summary:
        parts.append(
            f"\nUser-Provided Study Material Summary:\n{user_material_summary}\n"
            "Incorporate this material into your teaching. Reference it explicitly."
        )

    # 11. Extra context
    if extra_context:
        parts.append(f"\nAdditional Context:\n{extra_context}")

    return "\n\n".join(parts)


def compose_doubt_resolution_prompt(
    doubt_text: str,
    study_level: str,
    current_topic: str,
    ocr_text: Optional[str] = None,
) -> str:
    """Compose a user-message prompt for doubt resolution."""
    prompt = f"""The student has raised a doubt during the session.

Current topic being taught: {current_topic}
Student's study level: {study_level}

Student's doubt: {doubt_text}
"""
    if ocr_text:
        prompt += f"\nThe student also uploaded an image. OCR extracted text:\n{ocr_text}\n"

    prompt += """
Please answer this doubt clearly and simply, matching the student's study level.
After answering, smoothly transition back to the current topic.
"""
    return prompt


# ── Live doubt / MCQ streaming prompt ────────────────────────────────

_LIVE_DOUBT_MCQ_INSTRUCTIONS = """
RESPONSE FORMAT RULES — read carefully before responding.

Determine which of the two formats below fits the student's question:

────────────────────────────────────────────────────────────────────
FORMAT 1 — MCQ  (use when the student asks for a practice question,
quiz, test, or requests to be asked something — e.g. "ask me a
question", "test me", "give me an MCQ", "quiz me on this")

Output EXACTLY the following structure and NOTHING else:
MCQ_START
{"question": "Your question text here", "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option", "E) Do not know"], "correct_answer": "A", "explanation": "One or two sentences explaining why the correct answer is right."}
MCQ_END

Rules for MCQ format:
• Always include exactly 5 options labelled A) through E).
• Option E) must always be "Do not know" — verbatim.
• The correct_answer field contains only the letter (A, B, C, or D). Never E.
• The question must test understanding of the current topic.
• The explanation must be concise — 1 to 2 sentences maximum.
• Do NOT write any text before MCQ_START or after MCQ_END.

────────────────────────────────────────────────────────────────────
FORMAT 2 — Text explanation  (use for all other doubts and questions)

Answer clearly and concisely in plain text.
Keep sentences short — under 15 words each.
No bullet points. No markdown. Write as if speaking to the student.
"""


def compose_live_doubt_prompt(
    query_text: str,
    concept_name: str,
    segment_ctx: str = "",
) -> str:
    """Compose the user-message prompt for live streaming doubt/MCQ resolution.

    When the student's question is a quiz/practice request the model will
    respond with a structured MCQ block (MCQ_START … MCQ_END).  For all
    other questions it returns a plain-text explanation.
    """
    return (
        f"The student raised a question during the session.\n"
        f"Session topic: {concept_name}{segment_ctx}\n\n"
        f"Student's question: {query_text}\n"
        f"{_LIVE_DOUBT_MCQ_INSTRUCTIONS}"
    )


def compose_mcq_generation_prompt(topic: str, study_level: str, count: int = 3) -> str:
    """Compose a prompt for generating MCQ questions for pulse checks."""
    return f"""Generate {count} multiple-choice questions about "{topic}" at the {study_level} level.

For each question provide:
- The question text
- 4 options (A, B, C, D)
- The correct answer letter and text
- A brief explanation of why that answer is correct

Format as JSON array:
[{{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_answer": "A) ...", "explanation": "..."}}]
"""


def compose_segment_plan_prompt(
    concept_name: str,
    description: Optional[str],
    study_level: str,
    session_type: str,
    duration_minutes: Optional[int],
    user_material_summary: Optional[str] = None,
    plan_only: bool = False,
) -> str:
    """Compose a prompt for generating the session segment plan.

    If plan_only=True, returns a lighter prompt that skips content_script
    for all segments except segment_order=1 (the first one).
    """
    material_line = ("Use this student-provided material as primary reference:\n" + user_material_summary) if user_material_summary else ""

    if plan_only:
        prompt = f"""Plan a structured teaching session for the concept: "{concept_name}"

Description/Focus: {description or 'General coverage'}
Study Level: {study_level}
Session Type: {session_type}
{"Duration: " + str(duration_minutes) + " minutes" if duration_minutes else "Duration: Determine optimal based on topic complexity (max 180 minutes)"}

Create a segment PLAN. For each segment provide:
- segment_order (integer starting from 1)
- segment_type (one of: introduction, core_teaching, example, analogy, whiteboard, animation_demo, practice, qa_check, story, curiosity_trigger, recap, summary)
- title (descriptive title)
- duration_seconds (estimated duration)
- key_points (list of key concepts to cover)
- animation_cues (object describing any animations to show, or null)
- whiteboard_cues (object describing any whiteboard content, or null)
- teaching_notes (brief internal notes about approach)

IMPORTANT: ONLY for segment_order=1, also include:
- content_script (detailed teaching script for this first segment)

For all other segments, set content_script to null — it will be generated on demand later.

{material_line}

Return as a JSON array of segment objects.
Ensure the total duration fits within {"the " + str(duration_minutes) + " minute limit" if duration_minutes else "a reasonable timeframe"}.
Include variety in segment types for engagement.
"""
    else:
        prompt = f"""Plan a structured teaching session for the concept: "{concept_name}"

Description/Focus: {description or 'General coverage'}
Study Level: {study_level}
Session Type: {session_type}
{"Duration: " + str(duration_minutes) + " minutes" if duration_minutes else "Duration: Determine optimal based on topic complexity (max 180 minutes)"}

Create a detailed segment plan. Each segment should have:
- segment_order (integer starting from 1)
- segment_type (one of: introduction, core_teaching, example, analogy, whiteboard, animation_demo, practice, qa_check, story, curiosity_trigger, recap, summary)
- title (descriptive title)
- duration_seconds (estimated duration)
- content_script (detailed teaching script for this segment)
- teaching_notes (internal notes about approach)
- key_points (list of key concepts covered)
- animation_cues (object describing any animations to show, or null)
- whiteboard_cues (object describing any whiteboard content, or null)

{material_line}

Return as a JSON array of segment objects.
Ensure the total duration fits within {"the " + str(duration_minutes) + " minute limit" if duration_minutes else "a reasonable timeframe"}.
Include variety in segment types for engagement.
"""
    return prompt


def compose_segment_content_prompt(
    concept_name: str,
    segment_title: str,
    segment_type: str,
    segment_order: int,
    key_points: Optional[list] = None,
    teaching_notes: Optional[str] = None,
    study_level: str = "intermediate",
    personality: str = "very_friendly",
    mood: str = "focused",
    previous_segment_summary: Optional[str] = None,
    user_material_summary: Optional[str] = None,
    target_word_count: Optional[int] = None,
) -> str:
    """Compose a prompt for generating content_script for a single segment on demand."""
    points_str = ", ".join(key_points) if key_points else "General coverage"
    prev_context = f"\nContext from previous segment:\n{previous_segment_summary}" if previous_segment_summary else ""
    material_line = f"\nStudent-provided material:\n{user_material_summary}" if user_material_summary else ""

    word_count_line = (
        f"\nTARGET CONTENT LENGTH: Write approximately {target_word_count} words. "
        "Adjust depth and examples to match this target."
    ) if target_word_count else ""

    return f"""Generate a detailed teaching script for segment {segment_order} of a tutoring session.

Overall concept: "{concept_name}"
Segment title: "{segment_title}"
Segment type: {segment_type}
Key points to cover: {points_str}
Teaching notes: {teaching_notes or 'None'}
Study level: {study_level}
Tutor personality: {personality}
Student mood: {mood}
{prev_context}{material_line}{word_count_line}

Write a natural, spoken teaching script as if the tutor is speaking to the student live.
Include emotion markers like [excited], [calm], [curious] where appropriate.
Include pause markers like <pause:300ms> for natural pacing.
Include whiteboard/animation cues if relevant: [WHITEBOARD: action=write, content="..."] or [ANIMATION: type=diagram, description="..."]
Keep sentences ≤15 words for spoken clarity.

Return as JSON: {{"content_script": "...", "animation_cues": {{...}} or null, "whiteboard_cues": {{...}} or null}}
"""


def compose_notes_generation_prompt(segments_content: str, concept_name: str) -> str:
    """Compose a prompt for generating session notes/PDF content."""
    return f"""Based on the following teaching session content for "{concept_name}", generate comprehensive study notes.

Session Content:
{segments_content}

Generate:
1. content_markdown: Full notes in well-structured Markdown format with headers, bullet points, code blocks, and emphasis.
2. key_points: JSON array of the most important takeaways.
3. formulas: JSON array of any formulas or equations mentioned (as LaTeX strings).
4. diagrams: JSON array of diagram descriptions that should be included.

Format your response as JSON:
{{"content_markdown": "...", "key_points": [...], "formulas": [...], "diagrams": [...]}}
"""


def compose_session_evaluation_prompt(
    *,
    user_profession: str,
    concept_name: str,
    description: Optional[str] = None,
    study_level: str = "intermediate",
    entire_session_type: str = "intermediate",
    mood: str = "focused",
    personality: str = "very_friendly",
    language: str = "english",
    duration_type: str = "ai_determined",
    duration_minutes: Optional[int] = None,
    board_name: Optional[str] = None,
    class_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    chapter_name: Optional[str] = None,
    university: Optional[str] = None,
    course: Optional[str] = None,
    semester: Optional[int] = None,
    professional_background: Optional[str] = None,
    user_material_summary: Optional[str] = None,
) -> str:
    """Build the prompt that asks the AI to generate the session_evaluation JSON.

    The AI analyses ALL user inputs and produces a structured teaching plan:
    - What segments/topics to cover
    - Duration per segment
    - Teaching approach per segment
    - Total estimated duration
    """

    # Build context block based on profession
    context_lines: list[str] = [f"Profession: {user_profession}"]
    if user_profession == "student":
        context_lines += [
            f"Board: {board_name or 'Not specified'}",
            f"Class: {class_name or 'Not specified'}",
            f"Subject: {subject_name or 'Not specified'}",
            f"Chapter: {chapter_name or 'Not specified'}",
        ]
    elif user_profession == "college_student":
        context_lines += [
            f"University: {university or 'Not specified'}",
            f"Course: {course or 'Not specified'}",
            f"Semester: {semester or 'Not specified'}",
            f"Subject: {subject_name or 'Not specified'}",
            f"Chapter: {chapter_name or 'Not specified'}",
        ]
    elif user_profession == "working_professional":
        context_lines += [
            f"Professional Background: {professional_background or 'Not specified'}",
        ]
    # competitive_exams has no extra context fields

    context_block = "\n".join(context_lines)
    material_block = f"\nUser-uploaded study material content:\n{user_material_summary}" if user_material_summary else ""

    duration_info = (
        f"{duration_minutes} minutes (set by the student)"
        if duration_type == "user_defined" and duration_minutes
        else "Determine the optimal duration based on topic complexity (max 180 minutes)"
    )

    return f"""You are an expert curriculum designer and teaching strategist.

Evaluate ALL the information below and generate a comprehensive session evaluation plan in JSON.

──────────── Student Information ────────────
{context_block}

──────────── Session Configuration ────────────
Concept / Topic: {concept_name}
Description / Focus: {description or 'No specific focus'}
Study Level: {study_level}
Session Type: {entire_session_type}
Language: {language}
Student Mood: {mood}
Tutor Personality: {personality}
Duration: {duration_info}
{material_block}

──────────── Your Task ────────────
Analyse all the inputs above thoroughly. Then produce a structured JSON object with:

1. "session_overview" — object:
   - "main_concept": The main teaching concept (string)
   - "description": Brief overview of what the session covers (string)
   - "target_audience": Who this session is designed for (string)
   - "estimated_total_duration_seconds": Total session duration in seconds (int)
   - "difficulty_rating": 1–5 scale (int)
   - "prerequisites": List of concepts the student should already know (array of strings)

2. "segments" — array of objects, each containing:
   - "segment_order": Sequential number starting from 1 (int)
   - "segment_type": One of: introduction, core_teaching, example, analogy, whiteboard, animation_demo, practice, qa_check, story, curiosity_trigger, recap, summary
   - "title": Descriptive title (string)
   - "description": What this segment covers (string)
   - "key_points": Array of key concepts/points (array of strings)
   - "duration_seconds": Estimated duration in seconds (int)
   - "teaching_approach": How to teach this segment (string)
   - "visual_aids": Array of suggested visual aids — e.g. "diagram of X", "formula Y on whiteboard" (array of strings)

3. "teaching_strategy" — object:
   - "personality_approach": How the tutor personality should manifest (string)
   - "mood_adaptation": How to adapt to the student's current mood (string)
   - "engagement_techniques": List of techniques to keep the student engaged (array of strings)
   - "language_style": Notes about language and vocabulary level (string)

{"4. IMPORTANT — The user has uploaded study material. You MUST incorporate this material into your evaluation. Reference specific content from the material in the segments. Prioritize the material's topics and structure." if user_material_summary else ""}

Return ONLY valid JSON. No markdown formatting, no explanation outside the JSON.
"""


def compose_session_goodbye_prompt(
    tutor_name: str,
    concept_name: str,
    personality: str,
    language: str,
    segments_completed: int,
    total_segments: int,
) -> str:
    """Compose the prompt for the tutor's goodbye message at session end."""
    return f"""You are {tutor_name}, an experienced tutor. The tutoring session on "{concept_name}" is ending now.

The student completed {segments_completed} out of {total_segments} segments.
Your personality: {personality}.
Language: {language}.

Generate a warm, human goodbye message. It should:
1. Briefly acknowledge what was covered.
2. Encourage the student and celebrate their effort.
3. Suggest one or two things they can do next to reinforce learning.
4. End with a natural, warm farewell — like a real teacher would.

Keep it under 100 words. Write in spoken style (for text-to-speech).
Include emotion markers like [warm], [encouraging].
Include pause markers like <pause:400ms> for natural pacing.
"""


def compose_session_teaching_prompt(
    session_evaluation: dict,
    segment_order: int,
    system_prompt: str,
    previous_segment_summary: Optional[str] = None,
    user_material_summary: Optional[str] = None,
    target_word_count: Optional[int] = None,
) -> str:
    """Compose the user message that tells the AI to teach a specific segment,
    guided by the session_evaluation data."""

    segments = session_evaluation.get("segments", [])
    target_segment = None
    for seg in segments:
        if seg.get("segment_order") == segment_order:
            target_segment = seg
            break

    if not target_segment:
        target_segment = {
            "title": f"Segment {segment_order}",
            "description": "Continue teaching the topic.",
            "key_points": [],
            "teaching_approach": "Explain clearly.",
            "visual_aids": [],
        }

    overview = session_evaluation.get("session_overview", {})
    strategy = session_evaluation.get("teaching_strategy", {})

    prev_ctx = f"\nPrevious segment summary:\n{previous_segment_summary}" if previous_segment_summary else ""
    material_ctx = f"\nStudent study material:\n{user_material_summary}" if user_material_summary else ""
    dur_secs = target_segment.get("duration_seconds", 300)
    word_count_instruction = (
        f"\nTARGET CONTENT LENGTH: Write approximately {target_word_count} words for this segment. "
        f"This matches the {dur_secs}s duration at the expected speaking pace. "
        "Adjust depth, examples, and elaboration to hit this target — do not cut short."
    ) if target_word_count else ""

    return f"""Now teach segment {segment_order}: "{target_segment.get('title', '')}"

Session concept: {overview.get('main_concept', '')}
Segment description: {target_segment.get('description', '')}
Key points to cover: {', '.join(target_segment.get('key_points', []))}
Teaching approach: {target_segment.get('teaching_approach', '')}
Suggested visual aids: {', '.join(target_segment.get('visual_aids', []))}
Duration target: {dur_secs} seconds

Personality approach: {strategy.get('personality_approach', '')}
Mood adaptation: {strategy.get('mood_adaptation', '')}
Engagement techniques: {', '.join(strategy.get('engagement_techniques', []))}
{prev_ctx}{material_ctx}

Teach this segment now. Speak naturally as if directly to the student.
Follow the speech-first rules: short sentences, emotion markers, pause markers.
Use [WHITEBOARD:] and [ANIMATION:] cues where the visual aids suggest them.
{word_count_instruction}"""
