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

I evaluated the recommender against three normal taste profiles plus three
adversarial / edge-case profiles, using `python -m src.evaluate`. The profiles
are defined in [`src/evaluate.py`](src/evaluate.py).

### Normal profiles

**High-Energy Pop** — `{"genre": "pop", "mood": "happy", "energy": 0.9}`

```
1. Sunrise City by Neon Echo  (Score: 3.92)
   Why: genre match: pop (+2.0), mood match: happy (+1.0), energy 0.82 vs target 0.90 (+0.92)
2. Gym Hero by Max Pulse  (Score: 2.97)
   Why: genre match: pop (+2.0), energy 0.93 vs target 0.90 (+0.97)
3. Rooftop Lights by Indigo Parade  (Score: 1.86)
   Why: mood match: happy (+1.0), energy 0.76 vs target 0.90 (+0.86)
4. Basement Signal by Null Sector  (Score: 1.00)
   Why: energy 0.90 vs target 0.90 (+1.00)
5. Storm Runner by Voltline  (Score: 0.99)
   Why: energy 0.91 vs target 0.90 (+0.99)
```

**Chill Lofi** — `{"genre": "lofi", "mood": "chill", "energy": 0.3}`

```
1. Library Rain by Paper Lanterns  (Score: 3.95)
   Why: genre match: lofi (+2.0), mood match: chill (+1.0), energy 0.35 vs target 0.30 (+0.95)
2. Midnight Coding by LoRoom  (Score: 3.88)
   Why: genre match: lofi (+2.0), mood match: chill (+1.0), energy 0.42 vs target 0.30 (+0.88)
3. Focus Flow by LoRoom  (Score: 2.90)
   Why: genre match: lofi (+2.0), energy 0.40 vs target 0.30 (+0.90)
4. Spacewalk Thoughts by Orbit Bloom  (Score: 1.98)
   Why: mood match: chill (+1.0), energy 0.28 vs target 0.30 (+0.98)
5. Paper Boats by Wren Hollow  (Score: 1.00)
   Why: energy 0.30 vs target 0.30 (+1.00)
```

**Deep Intense Rock** — `{"genre": "rock", "mood": "intense", "energy": 0.95}`

```
1. Storm Runner by Voltline  (Score: 3.96)
   Why: genre match: rock (+2.0), mood match: intense (+1.0), energy 0.91 vs target 0.95 (+0.96)
2. Gym Hero by Max Pulse  (Score: 1.98)
   Why: mood match: intense (+1.0), energy 0.93 vs target 0.95 (+0.98)
3. Neon Overdrive by Pulsewave  (Score: 1.00)
   Why: energy 0.95 vs target 0.95 (+1.00)
4. Iron Verdict by Ashen Crown  (Score: 0.97)
   Why: energy 0.98 vs target 0.95 (+0.97)
5. Basement Signal by Null Sector  (Score: 0.95)
   Why: energy 0.90 vs target 0.95 (+0.95)
```

All three behave as designed: the song matching genre **and** mood tops the
list, followed by partial matches, then energy-only near-misses.

### Adversarial / edge-case profiles

**Conflicting preferences (sad mood + high energy)** — `{"genre": "folk", "mood": "sad", "energy": 0.9}`

```
1. Paper Boats by Wren Hollow  (Score: 3.40)
   Why: genre match: folk (+2.0), mood match: sad (+1.0), energy 0.30 vs target 0.90 (+0.40)
2. Basement Signal by Null Sector  (Score: 1.00)
   Why: energy 0.90 vs target 0.90 (+1.00)
3. Storm Runner by Voltline  (Score: 0.99)
   Why: energy 0.91 vs target 0.90 (+0.99)
4. Gym Hero by Max Pulse  (Score: 0.97)
   Why: energy 0.93 vs target 0.90 (+0.97)
5. Neon Overdrive by Pulsewave  (Score: 0.95)
   Why: energy 0.95 vs target 0.90 (+0.95)
```

*Finding:* the categorical bonuses (+3.0 for genre+mood) **overpower** the energy
signal. Paper Boats wins despite earning only +0.40 on energy — a sad *folk*
song, not the high-energy track the `energy: 0.9` field asked for. The system
silently resolves the contradiction in favor of genre/mood and never signals
that the request was self-contradictory.

**Unknown genre** — `{"genre": "polka", "mood": "happy", "energy": 0.5}`

```
1. Rooftop Lights by Indigo Parade  (Score: 1.74)
   Why: mood match: happy (+1.0), energy 0.76 vs target 0.50 (+0.74)
2. Sunrise City by Neon Echo  (Score: 1.68)
   Why: mood match: happy (+1.0), energy 0.82 vs target 0.50 (+0.68)
3. Velvet Hours by Sable Moon  (Score: 1.00)
   Why: energy 0.50 vs target 0.50 (+1.00)
4. Dust and Dirt Roads by Hollow Pines  (Score: 0.95)
   Why: energy 0.55 vs target 0.50 (+0.95)
5. Rainwater Blues by Delta Mabry  (Score: 0.95)
   Why: energy 0.45 vs target 0.50 (+0.95)
```

*Finding:* graceful degradation. A genre no song has simply earns 0 genre
points, so mood + energy decide the ranking. No crash, no empty result.

**Empty profile** — `{}`

```
1. Sunrise City by Neon Echo  (Score: 0.00)
   Why: a general suggestion for your profile
2. Midnight Coding by LoRoom  (Score: 0.00)
   Why: a general suggestion for your profile
3. Storm Runner by Voltline  (Score: 0.00)
   Why: a general suggestion for your profile
4. Library Rain by Paper Lanterns  (Score: 0.00)
   Why: a general suggestion for your profile
5. Gym Hero by Max Pulse  (Score: 0.00)
   Why: a general suggestion for your profile
```

*Finding:* with no preferences every song scores 0.00, so the "ranking" is
meaningless — Python's stable sort just returns the first five songs in **CSV
order**. The recommender should arguably detect an empty profile and refuse
rather than present catalog order as if it were a recommendation.

### Takeaways
- The scoring logic is **robust to malformed input** (unknown genre, empty dict) — it degrades instead of crashing.
- But it is **not robust to *contradictory* input**: it resolves conflicts silently by letting the heavier categorical weights win, which can produce a result that flatly ignores one of the user's stated preferences.
- When there is no signal, ranking collapses to arbitrary catalog order — a latent bias worth guarding against.

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



