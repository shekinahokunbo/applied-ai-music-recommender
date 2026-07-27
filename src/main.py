"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

try:
    # when run as a module from the repo root: python -m src.main
    from src.recommender import load_songs, recommend_songs
except ModuleNotFoundError:
    # when run as a script from inside src/: python main.py
    from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    profile = f"genre={user_prefs['genre']}, mood={user_prefs['mood']}, energy={user_prefs['energy']}"
    print("\n" + "=" * 60)
    print(f"  Top {len(recommendations)} recommendations for [{profile}]")
    print("=" * 60 + "\n")

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']}  by {song['artist']}")
        print(f"   Score: {score:.2f}")
        print(f"   Why:   {explanation}")
        print()


if __name__ == "__main__":
    main()
