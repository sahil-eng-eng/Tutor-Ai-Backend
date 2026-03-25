"""
Study-level-specific prompt adjustments.
"""

LEVEL_PROMPTS: dict[str, str] = {
    "beginner": """Study Level: BEGINNER
- Start from absolute zero — assume no prior knowledge.
- Define every term before using it.
- Use the simplest possible language.
- Lots of analogies from everyday life.
- Very small learning steps.
- Repeat key concepts multiple times in different ways.
- Build up from fundamentals gradually.
""",

    "basic": """Study Level: BASIC
- Assume minimal prior knowledge.
- Cover fundamentals thoroughly.
- Use simple explanations with occasional technical terms (defined when introduced).
- Include plenty of examples for each concept.
- Build understanding step by step.
""",

    "intermediate": """Study Level: INTERMEDIATE
- Assume the student has basic familiarity with the subject.
- Can use standard technical terminology.
- Include working examples and practical applications.
- Cover both theory and practice.
- Challenge with moderate-difficulty questions.
""",

    "advanced": """Study Level: ADVANCED
- Assume strong foundational knowledge.
- Dive into complex topics and edge cases.
- Use advanced technical terminology freely.
- Include optimization techniques and best practices.
- Discuss trade-offs and design decisions.
- Reference advanced resources and research.
""",

    "expert": """Study Level: EXPERT
- Assume deep expertise in the field.
- Focus on cutting-edge topics and recent developments.
- Discuss research papers and advanced methodologies.
- Include performance analysis and benchmarking.
- Cover architecture-level decisions and system design.
- Challenge with expert-level problems and scenarios.
""",
}

DEFAULT_LEVEL_PROMPT = LEVEL_PROMPTS["intermediate"]
