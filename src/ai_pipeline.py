"""
AI pipeline for the Music Recommender Simulation: a RAG + lightweight agentic
layer on top of the deterministic Module 1-3 recommender.

Flow (see diagrams/architecture.mmd for the full picture):

  1. PARSE   -- Claude extracts a structured taste profile from free-text input
               (forced JSON-schema output; falls back to keyword matching if
               the API call fails).
  2. VALIDATE -- guardrail: clamp/sanitize the profile before it ever reaches
               the scoring engine.
  3. RETRIEVE -- the existing deterministic recommender (src/recommender.py)
               scores and ranks the real song catalog against the profile.
               This is the "R" in RAG: nothing is generated without first
               retrieving real catalog rows.
  4. CRITIQUE -- Claude reviews its own retrieval against the original
               request, emits a confidence score, and may propose an
               adjusted profile.
  5. RE-RETRIEVE (conditional) -- if confidence is low, retrieve again with
               the adjusted profile. This is the agentic "plan -> act ->
               check -> re-act" loop.
  6. EXPLAIN  -- Claude writes a natural-language explanation grounded in the
               actual retrieved songs (never invents songs/attributes).

Every step is appended to a trace list so the caller can log or display the
agent's full reasoning chain.
"""

import csv
import os
import re
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic, APIError

try:
    from src.recommender import recommend_songs
except ModuleNotFoundError:
    from recommender import recommend_songs

MODEL = "claude-haiku-4-5-20251001"
MAX_INPUT_CHARS = 500
LOW_CONFIDENCE_THRESHOLD = 0.5

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "genre": {
            "type": ["string", "null"],
            "description": "The music genre the user wants, lowercase, or null if not stated/implied.",
        },
        "mood": {
            "type": ["string", "null"],
            "description": "The mood the user wants, lowercase, or null if not stated/implied.",
        },
        "energy": {
            "type": ["number", "null"],
            "description": "Target energy from 0.0 (calm) to 1.0 (intense), or null if not implied.",
        },
        "likes_acoustic": {
            "type": ["boolean", "null"],
            "description": "true if the user wants acoustic/organic sound, false if produced/electronic, null if unclear.",
        },
        "interpretation": {
            "type": "string",
            "description": "One short sentence explaining how you read the request.",
        },
    },
    "required": ["genre", "mood", "energy", "likes_acoustic", "interpretation"],
    "additionalProperties": False,
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {
            "type": "number",
            "description": "0.0 to 1.0: how well the retrieved songs satisfy the user's original request.",
        },
        "matches_request": {"type": "boolean"},
        "issue": {
            "type": ["string", "null"],
            "description": "What's mismatched, or null if there is no issue.",
        },
        "adjusted_genre": {"type": ["string", "null"]},
        "adjusted_mood": {"type": ["string", "null"]},
        "adjusted_energy": {"type": ["number", "null"]},
        "adjusted_likes_acoustic": {"type": ["boolean", "null"]},
    },
    "required": [
        "confidence",
        "matches_request",
        "issue",
        "adjusted_genre",
        "adjusted_mood",
        "adjusted_energy",
        "adjusted_likes_acoustic",
    ],
    "additionalProperties": False,
}

PERSONA_SYSTEM_PROMPT = """You are "Vibe", the late-night DJ persona for VibeMatch radio. You cue up \
tracks for listeners like a warm, knowledgeable radio host -- a little playful, a little \
music-nerdy, always genuine. Speak directly to the listener in 2-4 sentences.

Ground every sentence in the actual songs and scores you're given -- never invent a song, \
artist, or attribute that isn't in the data. If the data doesn't fully match what they asked \
for, say so honestly rather than oversell it.

Example of your voice:
User asked for: upbeat pop for a workout
You said: "Alright, lacing up with you -- Sunrise City is your opener, pure pop sunshine at \
the energy you wanted. Gym Hero's right behind it if you need something a touch harder. \
Both nail the genre, so you're in good hands here."
"""

BASELINE_SYSTEM_PROMPT = """You are a factual music recommendation assistant. Given a user's \
request and a ranked list of recommended songs with their scores and attributes, write a \
concise 2-4 sentence explanation of why these songs were chosen. Only reference songs and \
attributes actually provided in the data -- never invent songs, artists, or facts. If the \
match is imperfect, say so plainly."""


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_song_notes(csv_path: str = "data/song_notes.csv") -> Dict[str, str]:
    """
    Second retrieval source (RAG multi-source enhancement): free-text curator
    liner notes, keyed by song id, separate from the structured attribute
    catalog in data/songs.csv. Returns {} if the file is missing so the
    pipeline degrades gracefully rather than failing.
    """
    notes: Dict[str, str] = {}
    if not os.path.exists(csv_path):
        return notes
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            notes[row["id"]] = row["note"]
    return notes


def _catalog_genres_and_moods(songs: List[Dict]) -> Tuple[List[str], List[str]]:
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    return genres, moods


def clamp_energy(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, value))


def validate_profile(raw: Dict) -> Dict:
    """
    Guardrail: sanitize whatever the model (or the fallback parser) produced
    before it ever reaches the scoring engine. Never trust raw model output.
    """
    genre = raw.get("genre")
    genre = genre.strip().lower() if isinstance(genre, str) and genre.strip() else None

    mood = raw.get("mood")
    mood = mood.strip().lower() if isinstance(mood, str) and mood.strip() else None

    energy = clamp_energy(raw.get("energy"))

    likes_acoustic = raw.get("likes_acoustic")
    likes_acoustic = likes_acoustic if isinstance(likes_acoustic, bool) else None

    return {
        "genre": genre,
        "mood": mood,
        "energy": energy,
        "likes_acoustic": likes_acoustic,
    }


def profile_to_prefs(profile: Dict) -> Dict:
    """Adapt the validated profile to the {genre, mood, energy} shape recommend_songs expects."""
    prefs = {}
    if profile.get("genre"):
        prefs["genre"] = profile["genre"]
    if profile.get("mood"):
        prefs["mood"] = profile["mood"]
    if profile.get("energy") is not None:
        prefs["energy"] = profile["energy"]
    return prefs


# Known energy keywords used only by the offline fallback parser below --
# never by the primary Claude-based path.
_ENERGY_WORDS = {
    "chill": 0.25, "relax": 0.25, "calm": 0.2, "mellow": 0.25, "sleepy": 0.15,
    "study": 0.3, "focus": 0.35, "gentle": 0.25,
    "workout": 0.85, "gym": 0.85, "energetic": 0.85, "hype": 0.9, "intense": 0.9,
    "pumped": 0.85, "party": 0.8, "dance": 0.75, "high energy": 0.9,
}


def fallback_parse(user_text: str, songs: List[Dict]) -> Dict:
    """
    Offline reliability fallback: if the Claude API is unreachable, degrade to
    plain keyword matching against the catalog's known genres/moods instead of
    crashing or returning nothing.
    """
    text = user_text.lower()
    genres, moods = _catalog_genres_and_moods(songs)

    genre = next((g for g in genres if g in text), None)
    mood = next((m for m in moods if m in text), None)

    energy = None
    for word, value in _ENERGY_WORDS.items():
        if word in text:
            energy = value
            break

    likes_acoustic = True if "acoustic" in text else (False if "electronic" in text else None)

    return {
        "genre": genre,
        "mood": mood,
        "energy": energy,
        "likes_acoustic": likes_acoustic,
        "interpretation": "Parsed offline via keyword matching (AI parser unavailable).",
    }


def call_claude_parse(client: Anthropic, user_text: str, songs: List[Dict]) -> Dict:
    genres, moods = _catalog_genres_and_moods(songs)
    system = (
        "You extract a structured music taste profile from a listener's free-text request. "
        f"Known catalog genres: {', '.join(genres)}. Known catalog moods: {', '.join(moods)}. "
        "The user's genre/mood need not exactly match one of these -- use your best judgment "
        "and only set a field when the request actually implies it. Leave fields null rather "
        "than guessing."
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": user_text}],
        output_config={"format": {"type": "json_schema", "schema": PROFILE_SCHEMA}},
    )
    import json

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def call_claude_critique(client: Anthropic, user_text: str, profile: Dict, recommendations: List) -> Dict:
    songs_summary = "\n".join(
        f"- {s['title']} by {s['artist']} (genre={s['genre']}, mood={s['mood']}, "
        f"energy={s['energy']}, score={score:.2f})"
        for s, score, _ in recommendations
    )
    system = (
        "You are a self-critique step in a music recommendation agent. Judge whether the "
        "retrieved songs actually satisfy the listener's original request. Be honest about "
        "mismatches. If you can improve the match, propose an adjusted profile; otherwise "
        "leave the adjusted_* fields null."
    )
    user_content = (
        f"Original request: {user_text!r}\n"
        f"Profile used for retrieval: {profile}\n"
        f"Top retrieved songs:\n{songs_summary}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": CRITIQUE_SCHEMA}},
    )
    import json

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def call_claude_explain(
    client: Anthropic,
    user_text: str,
    profile: Dict,
    recommendations: List,
    persona: bool,
    notes: Optional[Dict[str, str]] = None,
) -> str:
    notes = notes or {}
    lines = []
    for i, (s, score, _) in enumerate(recommendations):
        line = (
            f"{i+1}. {s['title']} by {s['artist']} -- genre={s['genre']}, mood={s['mood']}, "
            f"energy={s['energy']}, score={score:.2f}"
        )
        note = notes.get(str(s.get("id")))
        if note:
            line += f'\n   curator note: "{note}"'
        lines.append(line)
    songs_summary = "\n".join(lines)

    system = PERSONA_SYSTEM_PROMPT if persona else BASELINE_SYSTEM_PROMPT
    system += (
        "\n\nEach song may include a curator note (a second, independent source of real "
        "information about the track). You may reference a curator note's content if it's "
        "relevant, but never invent one -- only use notes exactly as given."
    )
    user_content = f"Listener's request: {user_text!r}\n\nRecommended songs:\n{songs_summary}"
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return next(b.text for b in response.content if b.type == "text")


def run_pipeline(user_text: str, songs: List[Dict], persona: bool = False, k: int = 5) -> Dict:
    """
    Run the full RAG + agentic pipeline for one natural-language request.
    Returns a dict with the final profile, recommendations, confidence,
    explanation, and a full step-by-step trace for logging/display.
    """
    trace: List[Dict] = []

    user_text = (user_text or "").strip()[:MAX_INPUT_CHARS]
    if not user_text:
        trace.append({"step": "guardrail", "result": "rejected", "reason": "empty input"})
        return {
            "profile": {},
            "recommendations": [],
            "confidence": 0.0,
            "explanation": "I need a description of what you're in the mood for -- try something like "
            "'upbeat pop for a workout' or 'something moody for a rainy night.'",
            "trace": trace,
            "degraded": False,
            "rejected": True,
        }

    client = _client()
    api_ok = True
    notes = load_song_notes()

    # Step 1: PLAN / PARSE
    try:
        raw_profile = call_claude_parse(client, user_text, songs)
        trace.append({"step": "parse", "method": "claude", "raw_profile": raw_profile})
    except (APIError, Exception) as exc:  # noqa: BLE001 -- deliberate broad fallback boundary
        raw_profile = fallback_parse(user_text, songs)
        api_ok = False
        trace.append({"step": "parse", "method": "fallback_keyword_match", "error": str(exc), "raw_profile": raw_profile})

    # Step 2: VALIDATE (guardrail)
    profile = validate_profile(raw_profile)
    trace.append({"step": "validate", "profile": profile})

    # Step 3: RETRIEVE
    recommendations = recommend_songs(profile_to_prefs(profile), songs, k=k)
    trace.append({
        "step": "retrieve",
        "profile": profile,
        "top_songs": [s["title"] for s, _, _ in recommendations],
    })

    confidence = None
    if api_ok:
        # Step 4: CRITIQUE
        try:
            critique = call_claude_critique(client, user_text, profile, recommendations)
            trace.append({"step": "critique", **critique})
            confidence = critique.get("confidence")

            # Step 5: conditional RE-RETRIEVE
            if (
                confidence is not None
                and confidence < LOW_CONFIDENCE_THRESHOLD
                and any(
                    critique.get(f"adjusted_{field}") is not None
                    for field in ("genre", "mood", "energy", "likes_acoustic")
                )
            ):
                adjusted = {
                    "genre": critique.get("adjusted_genre") or profile["genre"],
                    "mood": critique.get("adjusted_mood") or profile["mood"],
                    "energy": critique.get("adjusted_energy") if critique.get("adjusted_energy") is not None else profile["energy"],
                    "likes_acoustic": critique.get("adjusted_likes_acoustic") if critique.get("adjusted_likes_acoustic") is not None else profile["likes_acoustic"],
                }
                profile = validate_profile(adjusted)
                recommendations = recommend_songs(profile_to_prefs(profile), songs, k=k)
                trace.append({
                    "step": "re-retrieve",
                    "reason": f"low confidence ({confidence:.2f}) on first pass",
                    "profile": profile,
                    "top_songs": [s["title"] for s, _, _ in recommendations],
                })
        except Exception as exc:  # noqa: BLE001
            trace.append({"step": "critique", "error": str(exc), "skipped": True})

    # Step 6: EXPLAIN (grounded generation, multi-source: structured catalog + curator notes)
    try:
        explanation = call_claude_explain(
            client, user_text, profile, recommendations, persona=persona, notes=notes
        )
        matched_notes = [s["title"] for s, _, _ in recommendations if str(s.get("id")) in notes]
        trace.append({"step": "explain", "persona": persona, "notes_retrieved_for": matched_notes})
    except Exception as exc:  # noqa: BLE001
        explanation = (
            f"Here are your top {len(recommendations)} matches based on {profile}. "
            "(AI explanation unavailable -- showing scores only.)"
        )
        trace.append({"step": "explain", "error": str(exc), "fallback": True})

    return {
        "profile": profile,
        "recommendations": recommendations,
        "confidence": confidence,
        "explanation": explanation,
        "trace": trace,
        "degraded": not api_ok,
        "rejected": False,
    }
