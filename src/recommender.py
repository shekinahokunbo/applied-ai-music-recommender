import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Scoring weights (the "Algorithm Recipe").
# These encode our opinion about what matters. Genre is worth more than mood
# because genre is the strongest, most stable identity of a song, while mood
# overlaps a lot with the numeric features (energy/valence). Tune these freely.
# ---------------------------------------------------------------------------
GENRE_MATCH_WEIGHT = 2.0
MOOD_MATCH_WEIGHT = 1.0
ENERGY_WEIGHT = 1.0
ACOUSTIC_WEIGHT = 1.0

# Numeric columns in data/songs.csv that must be parsed as floats.
NUMERIC_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def _closeness(value: float, target: float) -> float:
    """
    Reward a numeric feature for being CLOSE to the user's preference, in
    either direction -- not for being high or low. Both value and target are
    on a 0-1 scale, so the max possible gap is 1.0.

        closeness = 1 - |value - target|

    Perfect match -> 1.0, opposite end -> 0.0.
    """
    return 1.0 - abs(value - target)


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """
        The SCORING RULE: judge one song against one user. Returns the numeric
        score plus a list of human-readable reasons for the explanation.
        """
        score = 0.0
        reasons: List[str] = []

        # Categorical matches: exact match earns a fixed bonus.
        if song.genre == user.favorite_genre:
            score += GENRE_MATCH_WEIGHT
            reasons.append(f"genre match: {song.genre} (+{GENRE_MATCH_WEIGHT:.1f})")
        if song.mood == user.favorite_mood:
            score += MOOD_MATCH_WEIGHT
            reasons.append(f"mood match: {song.mood} (+{MOOD_MATCH_WEIGHT:.1f})")

        # Numeric closeness: reward being near the target energy.
        energy_score = _closeness(song.energy, user.target_energy) * ENERGY_WEIGHT
        score += energy_score
        reasons.append(
            f"energy {song.energy:.2f} vs target {user.target_energy:.2f} (+{energy_score:.2f})"
        )

        # Acousticness: reward high if the user likes acoustic, low otherwise.
        acoustic_fit = song.acousticness if user.likes_acoustic else (1.0 - song.acousticness)
        acoustic_score = acoustic_fit * ACOUSTIC_WEIGHT
        score += acoustic_score
        kind = "acoustic" if user.likes_acoustic else "produced/electronic"
        reasons.append(f"{kind} fit (+{acoustic_score:.2f})")

        return score, reasons

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """
        The RANKING RULE: score every song, order best-first, keep the top k.
        """
        scored = [(song, self._score(user, song)[0]) for song in self.songs]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = self._score(user, song)
        if not reasons:
            return f"'{song.title}' is a general suggestion based on your profile."
        return f"'{song.title}' " + ", ".join(reasons) + "."


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dicts, converting the numeric
    columns from strings to floats.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for field in NUMERIC_FIELDS:
                row[field] = float(row[field])
            songs.append(row)
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    The SCORING RULE (functional version): score a single song dict against a
    user_prefs dict of the form {"genre": ..., "mood": ..., "energy": ...}.
    Returns (score, reasons).
    """
    score = 0.0
    reasons: List[str] = []

    if song["genre"] == user_prefs.get("genre"):
        score += GENRE_MATCH_WEIGHT
        reasons.append(f"genre match: {song['genre']} (+{GENRE_MATCH_WEIGHT:.1f})")
    if song["mood"] == user_prefs.get("mood"):
        score += MOOD_MATCH_WEIGHT
        reasons.append(f"mood match: {song['mood']} (+{MOOD_MATCH_WEIGHT:.1f})")

    target_energy = user_prefs.get("energy")
    if target_energy is not None:
        energy_score = _closeness(song["energy"], target_energy) * ENERGY_WEIGHT
        score += energy_score
        reasons.append(
            f"energy {song['energy']:.2f} vs target {target_energy:.2f} (+{energy_score:.2f})"
        )

    return score, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    The RANKING RULE (functional version): apply score_song to every song,
    order best-first, and return the top k as (song, score, explanation).
    Required by src/main.py
    """
    # 1. JUDGE: score every song in the catalog with score_song.
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons) if reasons else "a general suggestion for your profile"
        scored.append((song, score, explanation))

    # 2. RANK: sort highest-score-first and keep the top k.
    #    sorted() returns a NEW list, so the caller's `songs` is never reordered.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)
    return ranked[:k]
