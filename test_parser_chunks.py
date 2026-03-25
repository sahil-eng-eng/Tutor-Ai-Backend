"""Quick test: verify parse_script_to_sse_events behaviour with from_chunk."""
import asyncio
from app.utils.script_parser import parse_script_to_sse_events

SCRIPT = (
    "[warm] Welcome to Advanced Calculus! <pause:300ms> "
    "Today, we'll dive into integration and differentiation. "
    "These are fundamental concepts. "
    "[excited] Let's get started with derivatives. "
    "The derivative measures rate of change."
)

async def test():
    for fc in [0, 4, 100]:
        print(f"\n{'='*60}\n=== from_chunk={fc} ===\n{'='*60}")
        events = []
        async for ev in parse_script_to_sse_events(SCRIPT, 1, "Test", 300, 3, from_chunk=fc):
            events.append(ev.strip())
            print(ev.strip())
        print(f"Total events: {len(events)}")

asyncio.run(test())
