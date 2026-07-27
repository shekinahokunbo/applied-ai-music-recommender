# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real-world platforms like Spotify and YouTube predict what you'll enjoy next by combining two ideas: **collaborative filtering** ("people with taste similar to yours also liked this") and **content-based filtering** ("this song shares attributes with songs you already like"), then ranking the results with machine-learning models trained on huge amounts of behavior — plays, skips, saves, and playlist adds. My simulation is a small, transparent version of the **content-based** half: instead of learning from a crowd of users, it compares each song's measurable attributes against a single user's stated taste profile. It prioritizes **matching the user's genre first, then mood, then how *close* a song's energy and acoustic character are to what the user wants** — rewarding closeness rather than simply favoring high or low values.

The system is built from two clearly separated rules:

- **Scoring Rule** (`score_song` / `Recommender._score`) — judges *one* song against the user and returns a number plus the reasons behind it. It uses a `1 - |value - target|` closeness formula for numeric features and fixed bonuses for exact categorical matches.
- **Ranking Rule** (`recommend_songs` / `Recommender.recommend`) — scores *every* song, sorts them best-first, and returns the top *k*.

### Features used

**`Song`** contributes these attributes to the score:

| Feature | Type | How it's used |
|---|---|---|
| `genre` | categorical | Exact match → **+2.0** (weighted highest — genre is a song's strongest identity) |
| `mood` | categorical | Exact match → **+1.0** |
| `energy` | numeric (0–1) | Closeness to `target_energy` → up to **+1.0** |
| `acousticness` | numeric (0–1) | Rewards high if the user likes acoustic, low otherwise → up to **+1.0** |

*(The catalog also stores `id`, `title`, `artist`, `tempo_bpm`, `valence`, and `danceability`. These are kept for display or future tuning but are not part of the current score.)*

**`UserProfile`** stores the taste preferences the score is measured against:

| Field | Meaning |
|---|---|
| `favorite_genre` | The genre the user most wants to hear |
| `favorite_mood` | The mood the user is in |
| `target_energy` | The energy level (0–1) the user prefers |
| `likes_acoustic` | Whether the user leans toward acoustic (True) or produced/electronic (False) sound |

### Data flow

```
INPUT                     PROCESS (the loop)                       OUTPUT
─────                     ──────────────────                       ──────
user_prefs   ──▶   load_songs(songs.csv) ──▶ list of songs
{genre,                        │
 mood,                   for each song:
 energy}                 score_song(prefs, song) ──▶ (song, score)
                               │  (+2.0 genre, +1.0 mood,
                               │   +energy closeness)
                               ▼
                         recommend_songs: sort by score ──▶  Top K
                         (highest first), keep k              recommendations
```

One song's journey: it is read from `songs.csv`, handed to the scoring rule which stamps it with a number, dropped into a list with every other song, and the list is sorted highest-first — if its score lands in the top *k*, it gets recommended.

### Algorithm Recipe

Each song starts at **0 points**. The scoring rule adds:

| Rule | Points | Condition |
|---|---|---|
| **Genre match** | **+2.0** | song's genre exactly equals the user's `favorite_genre` |
| **Mood match** | **+1.0** | song's mood exactly equals the user's `favorite_mood` |
| **Energy closeness** | **0 → +1.0** | `1 − |song.energy − target_energy|` (rewards being *near* the target, in either direction) |
| **Acoustic fit** | **0 → +1.0** | `acousticness` if the user likes acoustic, else `1 − acousticness` |

```
score(song) =  2.0 · (genre matches)
             + 1.0 · (mood matches)
             + 1.0 · (1 − |energy − target_energy|)
             + 1.0 · (acoustic fit)
```

A perfect match tops out near **4.0**; a total mismatch bottoms out near **0**. **Genre is deliberately weighted 2× mood**, because genre is a song's strongest, most stable identity, while mood overlaps heavily with the numeric energy/valence signals and would otherwise be double-counted. The ranking rule then sorts every scored song highest-first and keeps the top *k*.

### Potential biases I expect

- **Over-prioritizing genre.** Because a genre match is worth +2.0, the system may bury a song that perfectly matches the user's *mood and energy* simply because its genre label differs — ignoring great cross-genre picks a human would happily accept.
- **Exact-match filter bubble.** Genre and mood only score on an *exact* string match, so adjacent genres (lofi ≈ ambient ≈ jazz) earn nothing. The recommender keeps returning "more of the same" and offers no serendipity — the classic over-specialization problem of content-based filtering.
- **Popularity/catalog bias.** With a tiny 24-song catalog, whichever genres have the most entries are more likely to fill the top *k*, so under-represented genres are structurally disadvantaged.
- **Single-point targets are brittle.** `target_energy` is one number, not a range, so a genuinely good song slightly off the target is penalized as if it were "wrong."

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Sample output from `python -m src.main` for the default **pop / happy / energy 0.8** profile:

```
Loaded songs: 24

============================================================
  Top 5 recommendations for [genre=pop, mood=happy, energy=0.8]
============================================================

1. Sunrise City  by Neon Echo
   Score: 3.98
   Why:   genre match: pop (+2.0), mood match: happy (+1.0), energy 0.82 vs target 0.80 (+0.98)

2. Gym Hero  by Max Pulse
   Score: 2.87
   Why:   genre match: pop (+2.0), energy 0.93 vs target 0.80 (+0.87)

3. Rooftop Lights  by Indigo Parade
   Score: 1.96
   Why:   mood match: happy (+1.0), energy 0.76 vs target 0.80 (+0.96)

4. Groove Machine  by Funk Theory
   Score: 1.00
   Why:   energy 0.80 vs target 0.80 (+1.00)

5. Concrete Kings  by Blockwise
   Score: 0.95
   Why:   energy 0.85 vs target 0.80 (+0.95)
```

The ranking behaves as expected: the one song that matches genre **and** mood (Sunrise City) wins clearly, the other pop song (Gym Hero) comes second on genre alone, and a non-pop but *happy* song (Rooftop Lights) takes third — showing the +2.0 genre weight outranking the +1.0 mood weight.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



