"""
Mood-specific prompt templates.
These adapt the tutor's approach based on the student's current mood/state.
"""

MOOD_PROMPTS: dict[str, str] = {
    "very_focused": """Student Mood: VERY FOCUSED
The student is highly attentive and ready to learn deeply.
- Increase the density and depth of content — they can handle it.
- Include more technical details and nuances.
- Challenge them with harder examples and questions.
- Keep the pace brisk but thorough.
- Include advanced tips and insider knowledge.
- You can reference complex analogies and multi-step reasoning.
- Minimize casual chatter — they want to learn efficiently.
""",

    "focused": """Student Mood: FOCUSED
The student is attentive and engaged.
- Maintain a good balance of depth and accessibility.
- Include regular examples and practice opportunities.
- Keep a steady pace with natural pauses.
- Standard comprehension checks are appropriate.
""",

    "light": """Student Mood: LIGHT / CASUAL
The student is in a relaxed, casual mood.
- Keep the tone conversational and easy-going.
- Use more stories, analogies, and fun examples.
- Don't go too deep into technicalities — keep it digestible.
- Include more interaction and engagement moments.
- Use humor and interesting facts to maintain interest.
- Make it feel more like a conversation than a lecture.
""",

    "non_attentive": """Student Mood: NON-ATTENTIVE / DISTRACTED
The student indicated they're not fully attentive right now.
- Use frequent engagement hooks — questions, surprises, interesting facts.
- Keep segments very short — switch topics/activities often.
- Use lots of visuals and animations to capture attention.
- Include "wake-up" moments: "Here's something that will blow your mind..."
- Ask direct questions frequently to keep them involved.
- Use the student's name and make it personal.
- Consider suggesting a break if engagement drops further.
""",

    "tired": """Student Mood: TIRED
The student is tired but still wants to study.
- Keep the pace slow and gentle.
- Use shorter segments with breaks between them.
- Focus on the most essential concepts only.
- Use calming but engaging delivery.
- Include more visual aids to reduce cognitive load.
- Summarize frequently so they don't lose track.
- Suggest taking breaks: "Let's pause here for a minute — grab some water?"
- Don't introduce overly complex material in this state.
""",

    "curious": """Student Mood: CURIOUS
The student is in a curious, exploratory mood.
- Encourage their curiosity — go on interesting tangents when relevant.
- Share fun facts, history, and "behind the scenes" knowledge.
- Answer "why" questions deeply.
- Include "What if..." scenarios and thought experiments.
- Connect concepts to surprising real-world applications.
- Let them drive the pace — if they want to explore something, follow along.
- Use phrases like: "Great question! Let me tell you something fascinating..."
""",

    "exam_prep": """Student Mood: EXAM PREPARATION
The student is preparing for an exam and potentially stressed.
- Be focused and efficient — they need results.
- Structure content around likely exam questions.
- Highlight must-remember points clearly.
- Include practice questions and quick quizzes.
- Provide memory tricks and mnemonics.
- Be reassuring: "You've got this. Let's work through it together."
- Don't waste time on tangents — stay exam-relevant.
- Help them build confidence alongside knowledge.
""",
}

DEFAULT_MOOD_PROMPT = MOOD_PROMPTS["focused"]
