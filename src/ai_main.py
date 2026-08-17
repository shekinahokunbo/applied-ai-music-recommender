"""
CLI for the AI-powered (RAG + agentic) music recommender.

Usage:
    python -m src.ai_main "I want something moody for a rainy commute"
    python -m src.ai_main "upbeat pop for a workout" --persona
    python -m src.ai_main            # interactive prompt

Every run appends its full reasoning trace to logs/agent_traces.jsonl, which
ai_interactions.md links to as the committed record of the agent's
intermediate reasoning.
"""

import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

try:
    from src.ai_pipeline import run_pipeline
    from src.recommender import load_songs
except ModuleNotFoundError:
    from ai_pipeline import run_pipeline
    from recommender import load_songs

TRACE_LOG_PATH = os.path.join("logs", "agent_traces.jsonl")


def log_trace(user_text: str, result: dict) -> None:
    os.makedirs(os.path.dirname(TRACE_LOG_PATH), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": user_text,
        "profile": result["profile"],
        "confidence": result["confidence"],
        "degraded": result["degraded"],
        "trace": result["trace"],
    }
    with open(TRACE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def print_result(user_text: str, result: dict) -> None:
    print("\n" + "=" * 64)
    print(f"  Request: {user_text!r}")
    print("=" * 64)

    print("\n--- Agent trace ---")
    for step in result["trace"]:
        name = step.get("step")
        detail = {k: v for k, v in step.items() if k != "step"}
        print(f"[{name}] {detail}")

    if result["rejected"]:
        print("\n" + result["explanation"])
        return

    print(f"\n--- Recommendations (confidence: {result['confidence']}) ---")
    for rank, (song, score, explanation) in enumerate(result["recommendations"], start=1):
        print(f"{rank}. {song['title']} by {song['artist']}  (score: {score:.2f})")
        print(f"   {explanation}")

    print("\n--- AI explanation ---")
    print(result["explanation"])

    if result["degraded"]:
        print("\n[NOTE] AI parsing was unavailable this run; used offline keyword fallback.")


def main() -> None:
    load_dotenv()
    if "ANTHROPIC_API_KEY" not in os.environ:
        print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    persona = "--persona" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--persona"]

    if args:
        user_text = " ".join(args)
    else:
        user_text = input("What are you in the mood for? ")

    songs = load_songs("data/songs.csv")
    result = run_pipeline(user_text, songs, persona=persona)
    print_result(user_text, result)
    log_trace(user_text, result)


if __name__ == "__main__":
    main()
