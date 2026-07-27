# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeMatch 1.0**

A tiny music recommender. It matches songs to your taste.

---

## 2. Intended Use and Non-Intended Use

**Goal / Task:** VibeMatch tries to guess which songs you will like. You give it a taste profile. It suggests songs from its catalog that fit.

**Intended use:** This is a classroom project. It is for learning how content-based recommenders work. It assumes you can name a favorite genre, a mood, and an energy level (calm or intense).

**Non-intended use:** This is not for real users or real music apps. Do not use it to make real decisions. The catalog is tiny and made up. It should not be used to judge artists or rank real music.

---

## 3. How the Model Works (Algorithm Summary)

Every song has a genre, a mood, and some numbers like energy. You tell the model what you like. Then the model gives each song points.

The rules are simple:

- **+2 points** if the song's genre matches yours.
- **+1 point** if the song's mood matches yours.
- **up to +1 point** for how close the song's energy is to what you want.

Genre is worth the most because it is the strongest sign of what a song is like. After every song has points, the model sorts them from most points to fewest. It shows you the top few. It also tells you *why* each song was picked.

**What I changed from the starter:** the starter had empty functions. I wrote the scoring rule and the ranking rule. I made the model list its reasons with points. I grew the catalog from 10 songs to 24.

---

## 4. Data (Data Used)

The catalog is a CSV file with **24 songs**. Each song has these fields: id, title, artist, genre, mood, energy, tempo, valence, danceability, and acousticness.

There are 21 genres (like pop, lofi, rock, jazz, metal, and gospel) and 20 moods (like happy, chill, intense, sad, and dark). I added 14 songs to the original 10 to cover more genres and moods.

**Limits:** The dataset is tiny and made up. The model only uses 4 fields to score (genre, mood, energy, acousticness). There is no real listening history. There are no lyrics and no language info. Whole styles of music are missing.

---

## 5. Strengths  

The model works well for clear, simple tastes. If you ask for chill lofi, you get chill lofi. If you ask for intense rock, the intense rock song comes first.

It always explains its picks. You can see the exact points behind every song. This makes it easy to trust and easy to debug.

It never crashes on strange input. A made-up genre or an empty profile still returns a list. For the three normal profiles I tested, the top picks matched my own musical intuition.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

The main weakness I discovered is an **exact-match genre filter bubble** that the energy gap cannot correct. Genre is only rewarded on an *exact string match*, so musically adjacent genres earn nothing — in my "Deep Intense Rock" test, a metal track (*Iron Verdict*, energy 0.98) was ranked **below** an EDM track (*Neon Overdrive*, energy 0.95) simply because metal got zero genre credit and lost the tiebreak by a 0.03 energy gap, even though metal is far closer to rock than EDM is. This also unfairly disadvantages **moderate / eclectic listeners**: because the energy score is `1 − |gap|`, a user with a mid-range target (≈0.5) sees every song's energy compressed into a narrow high-scoring band, so the energy signal barely differentiates anything and their ranking collapses onto whatever genre happens to match exactly. Notably this bias comes from the scoring logic, **not** dataset imbalance — the catalog is genre-balanced (lofi 3, pop 2, all others 1 of 24), so the unfairness is baked into how points are awarded rather than into the data. The fix is to give genre *partial* credit through a similarity map (rock ≈ metal ≈ punk) so near-neighbors are no longer treated as total strangers.

### Other prompts to consider
- Features it does not consider (tempo, valence, danceability are stored but unused in the score)
- Genres or moods that are underrepresented
- Cases where the system overfits to one preference (conflicting profiles: genre+mood silently override a contradictory energy target)
- Ways the scoring might unintentionally favor some users (extreme-preference users get sharper rankings than moderate ones)

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

### Profiles I tested

I ran six user profiles through the recommender (see [`src/evaluate.py`](src/evaluate.py)): three "normal" listeners and three tricky ones.

- **High-Energy Pop** — pop, happy, energy 0.9
- **Chill Lofi** — lofi, chill, energy 0.3
- **Deep Intense Rock** — rock, intense, energy 0.95
- **Conflicting** — folk, sad, but energy 0.9 (a sad mood usually means *calm* music, so this profile contradicts itself)
- **Unknown genre** — asks for "polka," which no song in the catalog is
- **Empty** — no preferences at all

### What surprised me

The biggest surprise was the **Conflicting** profile. When I asked for a sad *and* high-energy song, the system confidently returned a quiet, sad folk song (*Paper Boats*) and completely ignored the "high energy" request. It never warned me that my two wishes couldn't both be satisfied — it just quietly picked the mood over the energy. The second surprise was the **Empty** profile: with nothing to go on, it still returned a top-5 list, but the songs were just the first five in the spreadsheet — a "recommendation" that isn't really a recommendation at all.

### Comparing profiles (plain language)

- **High-Energy Pop vs. Chill Lofi:** These are near opposites, and the outputs reflect that perfectly. The pop listener gets bright, upbeat songs (Sunrise City, Gym Hero); the lofi listener gets quiet study-music (Library Rain, Midnight Coding). This makes sense because the two profiles disagree on *all three* things that matter — genre, mood, and energy — so there is zero overlap in their top songs. This is the system working exactly as intended.

- **High-Energy Pop vs. Deep Intense Rock:** Both want loud, high-energy music, so they *share* the high-energy tracks lower down their lists (Gym Hero shows up for both). The difference is at the very top: the pop fan's #1 is a happy pop song, the rock fan's #1 is an intense rock song. This makes sense — they agree on *energy* but disagree on *genre and mood*, so the songs they share are the energetic ones, while their top picks split apart on style.

- **Chill Lofi vs. Deep Intense Rock:** These have basically nothing in common, and the lists prove it — one is full of calm 0.3-energy tracks, the other full of 0.95-energy tracks. A song that scores well for one scores near the bottom for the other, which is the behavior you'd want from a system that actually understands the difference between "relax" and "work out."

- **Normal profiles vs. edge cases:** The three normal profiles all produced sensible, varied lists. The edge cases showed the limits — the Unknown-genre profile degraded gracefully (it fell back on mood and energy), but the Conflicting and Empty profiles revealed that the system will always hand back *something*, even when the request is contradictory or blank.

### Why "Gym Hero" keeps showing up for "Happy Pop"

Imagine the recommender giving out points. A song earns **2 points** for being the right *genre* (pop), **1 point** for being the right *mood* (happy), and up to **1 more point** for having roughly the *energy* the listener wants. "Gym Hero" is a pop song with very high energy, so it collects the 2 genre points and nearly a full energy point — even though its mood is "intense," not "happy." That's enough to land it near the top of any *pop* listener's list. In short: **because we made genre worth the most points, any pop song is hard to beat — even one whose mood doesn't quite fit.** It keeps appearing not because it's a perfect match, but because matching the genre alone is worth more than matching the mood, and Gym Hero nails the genre.

---

## 8. Future Work (Ideas for Improvement)

1. **Give partial credit for similar genres.** Rock should count a little for a metal fan. This would break the filter bubble I found.
2. **Use the features I am ignoring.** Tempo, valence, and danceability are in the data but not in the score. Adding them would make picks richer.
3. **Handle bad profiles honestly.** Warn the user when a profile is empty or contradictory, instead of guessing and returning a list anyway.

---

## 9. Personal Reflection  

**My biggest learning moment** was seeing that a recommendation is just points and sorting. Once I split the work into two rules — a scoring rule for one song, and a ranking rule for the whole list — the whole thing clicked. It stopped feeling like magic.

**AI tools helped me** move fast. They helped me write the scoring and ranking code and explain the tricky parts in plain words. They also suggested edge-case profiles I would not have thought of, like the sad-but-high-energy user. But I had to double-check them. For example, one suggested bias was "the system over-favors pop because most songs are pop." I checked the real data and that was not true — my catalog is balanced. So the honest bias was in my scoring logic, not the data. Checking the numbers myself mattered.

**What surprised me** is how a simple algorithm can still feel like a real recommender. There is no machine learning here. It is just points and a sort. But it gives sensible picks and even explains itself, so it feels smart.

**If I kept going,** I would add a genre-similarity map, use the extra song features, and try collaborative filtering with a bigger, real dataset. That would move it closer to how Spotify actually works.
