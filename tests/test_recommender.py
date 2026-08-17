from src.recommender import Song, UserProfile, Recommender
from src.ai_pipeline import validate_profile, clamp_energy, fallback_parse, profile_to_prefs

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# --- AI pipeline guardrail tests (pure logic, no API calls, run offline) ---

def test_clamp_energy_bounds_out_of_range_values():
    assert clamp_energy(1.5) == 1.0
    assert clamp_energy(-0.3) == 0.0
    assert clamp_energy(0.42) == 0.42
    assert clamp_energy(None) is None
    assert clamp_energy("not a number") is None


def test_validate_profile_sanitizes_model_output():
    raw = {"genre": "  Pop  ", "mood": "", "energy": 1.7, "likes_acoustic": "yes"}
    profile = validate_profile(raw)
    assert profile == {"genre": "pop", "mood": None, "energy": 1.0, "likes_acoustic": None}


def test_validate_profile_handles_missing_keys():
    profile = validate_profile({})
    assert profile == {"genre": None, "mood": None, "energy": None, "likes_acoustic": None}


def test_profile_to_prefs_omits_unset_fields():
    profile = {"genre": "rock", "mood": None, "energy": 0.5, "likes_acoustic": None}
    assert profile_to_prefs(profile) == {"genre": "rock", "energy": 0.5}


def test_fallback_parse_matches_known_catalog_terms():
    songs = [
        {"genre": "lofi", "mood": "chill", "energy": 0.4},
        {"genre": "rock", "mood": "intense", "energy": 0.9},
    ]
    profile = fallback_parse("something chill and lofi to relax to", songs)
    assert profile["genre"] == "lofi"
    assert profile["mood"] == "chill"
    assert profile["energy"] == 0.25  # matched on "relax"


def test_fallback_parse_returns_nulls_for_unrecognized_text():
    songs = [{"genre": "lofi", "mood": "chill", "energy": 0.4}]
    profile = fallback_parse("zzz qqq xyz123", songs)
    assert profile["genre"] is None
    assert profile["mood"] is None
    assert profile["energy"] is None
