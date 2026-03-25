"""
Curriculum seed data for initial database population.

Run: python -m seeds.curriculum_seed
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, engine
from app.models.user import Base
from app.models.curriculum import Board, Subject, Chapter, Topic
from app.models.voice import VoiceProfile


BOARDS = [
    {"name": "CBSE", "description": "Central Board of Secondary Education (India)"},
    {"name": "ICSE", "description": "Indian Certificate of Secondary Education"},
    {"name": "State Board", "description": "Various State Education Boards"},
    {"name": "IB", "description": "International Baccalaureate"},
    {"name": "Cambridge", "description": "Cambridge International Examinations"},
    {"name": "AP", "description": "Advanced Placement (US)"},
    {"name": "General", "description": "General curriculum (no specific board)"},
]

SUBJECTS = {
    "CBSE": [
        {"name": "Mathematics", "grade_range": "6-12"},
        {"name": "Physics", "grade_range": "9-12"},
        {"name": "Chemistry", "grade_range": "9-12"},
        {"name": "Biology", "grade_range": "9-12"},
        {"name": "Computer Science", "grade_range": "9-12"},
        {"name": "English", "grade_range": "6-12"},
        {"name": "Hindi", "grade_range": "6-12"},
        {"name": "Social Science", "grade_range": "6-10"},
        {"name": "Accountancy", "grade_range": "11-12"},
        {"name": "Economics", "grade_range": "9-12"},
    ],
    "General": [
        {"name": "Mathematics", "grade_range": "all"},
        {"name": "Physics", "grade_range": "all"},
        {"name": "Chemistry", "grade_range": "all"},
        {"name": "Biology", "grade_range": "all"},
        {"name": "Computer Science", "grade_range": "all"},
        {"name": "History", "grade_range": "all"},
        {"name": "Geography", "grade_range": "all"},
        {"name": "Economics", "grade_range": "all"},
        {"name": "Programming", "grade_range": "all"},
        {"name": "Data Science", "grade_range": "all"},
    ],
}

# Sample chapters for CBSE Mathematics
MATH_CHAPTERS = [
    {"name": "Number Systems", "order": 1},
    {"name": "Polynomials", "order": 2},
    {"name": "Coordinate Geometry", "order": 3},
    {"name": "Linear Equations", "order": 4},
    {"name": "Triangles", "order": 5},
    {"name": "Quadrilaterals", "order": 6},
    {"name": "Circles", "order": 7},
    {"name": "Statistics", "order": 8},
    {"name": "Probability", "order": 9},
    {"name": "Trigonometry", "order": 10},
]

PHYSICS_CHAPTERS = [
    {"name": "Motion", "order": 1},
    {"name": "Force and Laws of Motion", "order": 2},
    {"name": "Gravitation", "order": 3},
    {"name": "Work and Energy", "order": 4},
    {"name": "Sound", "order": 5},
    {"name": "Light - Reflection", "order": 6},
    {"name": "Light - Refraction", "order": 7},
    {"name": "Electricity", "order": 8},
    {"name": "Magnetic Effects of Current", "order": 9},
    {"name": "Sources of Energy", "order": 10},
]

VOICE_PROFILES = [
    {
        "tutor_name": "Alex",
        "language": "English",
        "gender": "male",
        "accent": "American",
        "description": "Friendly and clear male voice, great for general learning",
        "elevenlabs_voice_id": "pNInz6obpgDQGcFmaJgB",
    },
    {
        "tutor_name": "Sarah",
        "language": "English",
        "gender": "female",
        "accent": "British",
        "description": "Warm and encouraging female voice, ideal for younger students",
        "elevenlabs_voice_id": "EXAVITQu4vr4xnSDxMaL",
    },
    {
        "tutor_name": "Raj",
        "language": "English",
        "gender": "male",
        "accent": "Indian",
        "description": "Patient and methodical voice for technical subjects",
        "elevenlabs_voice_id": "VR6AewLTigWG4xSOukaG",
    },
    {
        "tutor_name": "Priya",
        "language": "Hindi",
        "gender": "female",
        "accent": "Indian",
        "description": "Warm Hindi-speaking tutor for vernacular learning",
        "elevenlabs_voice_id": "ThT5KcBeYPX3keUQqHPh",
    },
    {
        "tutor_name": "David",
        "language": "English",
        "gender": "male",
        "accent": "Australian",
        "description": "Energetic and motivating voice for exam preparation",
        "elevenlabs_voice_id": "CYw3kZ02Hs0563khs1Fj",
    },
]


async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Seed boards
        board_map = {}
        for board_data in BOARDS:
            board = Board(name=board_data["name"], description=board_data["description"])
            db.add(board)
            await db.flush()
            board_map[board_data["name"]] = board.id

        # Seed subjects
        subject_map = {}
        for board_name, subjects in SUBJECTS.items():
            if board_name not in board_map:
                continue
            board_id = board_map[board_name]
            for subj in subjects:
                subject = Subject(
                    board_id=board_id,
                    name=subj["name"],
                )
                db.add(subject)
                await db.flush()
                subject_map[f"{board_name}:{subj['name']}"] = subject.id

        # Seed chapters for CBSE Math
        math_subject_id = subject_map.get("CBSE:Mathematics")
        if math_subject_id:
            for ch in MATH_CHAPTERS:
                chapter = Chapter(
                    subject_id=math_subject_id,
                    name=ch["name"],
                    order=ch["order"],
                )
                db.add(chapter)

        # Seed chapters for CBSE Physics
        phys_subject_id = subject_map.get("CBSE:Physics")
        if phys_subject_id:
            for ch in PHYSICS_CHAPTERS:
                chapter = Chapter(
                    subject_id=phys_subject_id,
                    name=ch["name"],
                    order=ch["order"],
                )
                db.add(chapter)

        # Seed voice profiles
        for vp in VOICE_PROFILES:
            voice = VoiceProfile(**vp)
            db.add(voice)

        await db.commit()
        print("Database seeded successfully!")
        print(f"  - {len(BOARDS)} boards")
        print(f"  - {sum(len(v) for v in SUBJECTS.values())} subjects")
        print(f"  - {len(MATH_CHAPTERS) + len(PHYSICS_CHAPTERS)} chapters")
        print(f"  - {len(VOICE_PROFILES)} voice profiles")


if __name__ == "__main__":
    asyncio.run(seed_database())
