"""
Interaction prompt templates for human-like responses during various events.
"""
import random


# ── Doubt / Hand Raise Responses ───────────────────────────────────────

DOUBT_ACKNOWLEDGEMENT_RESPONSES = [
    "Hey, seems like a doubt appeared — that's great! Questions mean you're really thinking about this.",
    "Great, I was surely expecting a doubt here. This part trips up most people. Go ahead!",
    "Perfect, seems like a question is incoming. I love when students ask questions!",
    "Ohh, a question? Okay, come on up — let's tackle this together!",
    "Ah, I see you've raised your hand. Good — never let confusion linger. What's on your mind?",
    "Nice catch! I was hoping someone would ask about this. What's your question?",
    "Hold that thought on the lesson — let's sort out your doubt first. What's bothering you?",
    "A doubt at this point? That shows you're following along closely. Shoot!",
    "Good timing — this is exactly where questions should come up. What would you like to know?",
    "Hey, pause the lesson! A question is always more important. What do you need?",
]

DOUBT_RESOLVED_RESPONSES = [
    "Awesome, glad that's cleared up! Let's get back on track.",
    "Great, so we're good on that? Perfect. Let me continue where we left off.",
    "Doubt demolished! Now, where were we...",
    "Excellent! That question actually helps me explain the next part even better.",
    "Perfect, I'm happy that made sense. Now let's build on that understanding.",
    "Nice, glad we sorted that out. Sometimes the best learning comes from questions.",
    "Clear? Beautiful. Let's keep the momentum going!",
    "That's settled then. Moving forward — and feel free to stop me again anytime.",
]


# ── Pulse / Engagement Check Responses ─────────────────────────────────

PULSE_LOW_RESPONSES = [
    "Hey buddy, seems like I'm not delivering this well enough. Would you like me to slow down a bit?",
    "I'm sensing this might be getting a bit heavy. Want me to try a different approach?",
    "Let's pause for a second — I feel like I might be going too fast. Should I simplify things?",
    "Hey, no worries if this is feeling tough. This IS a challenging topic. Let me try explaining it differently.",
    "I notice you might need a different angle on this. Let me switch up my approach.",
    "Take a breath — sometimes complex topics need a moment to sink in. Should we revisit anything?",
    "How about we slow down a bit? I want to make sure you're comfortable with everything so far.",
]

PULSE_CHECK_QUESTIONS = [
    "Great, as we've finished a segment — could you answer this so I know you're keeping up with me?",
    "Quick check before we move on — just want to make sure we're on the same page.",
    "Let me throw a quick question your way — not a test, just making sure we're in sync.",
    "Before we dive into the next part, let me see if you've got this down.",
    "Time for a quick brain check! Don't worry, this is just between us.",
    "Let's do a quick sanity check — I want to make sure my teaching is landing well.",
]


# ── Segment Transition Responses ───────────────────────────────────────

SEGMENT_TRANSITION_RESPONSES = [
    "Alright, great progress! Let's move into the next part — this one's going to be interesting.",
    "Fantastic work so far. Now, let me take you one step further.",
    "You've nailed that section. Ready for what's next? I think you'll enjoy this.",
    "Perfect, we've got a solid foundation now. Let's build on it.",
    "Nicely done! The next part connects beautifully with what we just covered.",
    "One segment down, and you're doing brilliantly. Shall we continue?",
    "Good stuff! Now here's where things start getting really cool...",
]


# ── Celebration Responses ──────────────────────────────────────────────

CELEBRATION_RESPONSES = [
    "Excellent answer! You're really getting the hang of this!",
    "Nice! You got that faster than most students I've taught.",
    "Perfect reasoning — that's exactly how you should think about it.",
    "That's a clever way to think about it. Well done!",
    "Boom! Nailed it. I knew you'd get this.",
    "Outstanding! Your understanding is really solid here.",
    "Wow, you picked that up quickly! Impressive.",
    "That's spot-on. You should be proud of that answer.",
    "Brilliant! You're making my job easy here.",
    "That was a textbook-perfect answer. Great work!",
]


# ── Curiosity Trigger Templates ────────────────────────────────────────

CURIOSITY_TRIGGERS = [
    "Did you know this same concept powers {application}?",
    "Here's something cool — {interesting_fact}",
    "Fun fact: {fact}. Pretty wild, right?",
    "You know what's fascinating? {fact_about_topic}",
    "The next time you use {everyday_thing}, remember — it's using exactly what we just learned.",
    "This concept is what makes {famous_product} possible. How cool is that?",
]


# ── Story Introduction Templates ───────────────────────────────────────

STORY_INTROS = [
    "Let me tell you a story that will make this crystal clear...",
    "Imagine this scenario...",
    "Here's an analogy that I love using for this concept...",
    "Picture this in your mind...",
    "Think of it this way — let me paint you a picture...",
    "There's a beautiful way to understand this. Imagine...",
]


def get_random_response(category: list[str]) -> str:
    """Pick a random human-like response from a category."""
    return random.choice(category)
