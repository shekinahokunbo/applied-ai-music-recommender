"""
System evaluation harness for the Music Recommender Simulation.

Runs the recommender against several taste profiles -- including adversarial
and edge-case profiles designed to probe the scoring logic -- and prints the
top 5 results for each. Run with: python -m src.evaluate
"""

try:
    from src.recommender import load_songs, recommend_songs
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs


# Normal profiles plus adversarial / edge cases.
PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.9},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.3},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.95},
    # Adversarial: mood 'sad' implies calm, but energy 0.9 demands intensity.
    "Conflicting (sad + high energy)": {"genre": "folk", "mood": "sad", "energy": 0.9},
    # Edge case: a genre that does not exist in the catalog.
    "Unknown genre (polka)": {"genre": "polka", "mood": "happy", "energy": 0.5},
    # Edge case: empty profile -- no preferences at all.
    "Empty profile": {},
}


def show(name: str, user_prefs: dict, songs: list) -> None:
    recommendations = recommend_songs(user_prefs, songs, k=5)
    print("=" * 64)
    print(f"  {name}  ->  {user_prefs}")
    print("=" * 64)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} by {song['artist']}  (Score: {score:.2f})")
        print(f"   Why: {explanation}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")
    for name, prefs in PROFILES.items():
        show(name, prefs, songs)


if __name__ == "__main__":
    main()
