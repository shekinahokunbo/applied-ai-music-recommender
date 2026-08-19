"""
VibeMatch AI -- Streamlit front end.

A live, shareable demo of the RAG + agentic music recommender in src/ai_pipeline.py.
Deploy on Streamlit Community Cloud (main file: streamlit_app.py) and set
ANTHROPIC_API_KEY in the app's Secrets. See README.md for full setup docs.
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_pipeline import load_song_notes, run_pipeline
from src.recommender import load_songs

# ---------------------------------------------------------------------------
# API key resolution: Streamlit Cloud secrets first, then local .env / env var
# ---------------------------------------------------------------------------
load_dotenv()
if "ANTHROPIC_API_KEY" not in os.environ:
    try:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass

HAS_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))

st.set_page_config(
    page_title="VibeMatch AI",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling -- synthwave / neon aesthetic (matches the catalog's own vibe:
# artists like "Neon Echo" and songs like "Night Drive Loop")
# ---------------------------------------------------------------------------
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
    --pink: #ff4d97;
    --cyan: #22e2d6;
    --purple: #9d4edd;
    --ink: #f5f0ff;
    --muted: #b8a9d9;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3, .vm-title { font-family: 'Space Grotesk', sans-serif; }

.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(255,77,151,0.16), transparent 42%),
        radial-gradient(circle at 85% 15%, rgba(34,226,214,0.14), transparent 45%),
        radial-gradient(circle at 50% 100%, rgba(157,78,221,0.18), transparent 55%),
        #0d0221;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #150730 0%, #0d0221 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}

/* Hero */
.vm-hero {
    padding: 2.2rem 2.4rem;
    border-radius: 22px;
    margin-bottom: 1.6rem;
    background: linear-gradient(120deg, rgba(255,77,151,0.16), rgba(34,226,214,0.08) 55%, rgba(157,78,221,0.16));
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 0 60px rgba(255,77,151,0.08);
}
.vm-eyebrow {
    display: inline-block;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--cyan);
    background: rgba(34,226,214,0.1);
    border: 1px solid rgba(34,226,214,0.35);
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    margin-bottom: 0.9rem;
    font-weight: 600;
}
.vm-title {
    font-size: 2.6rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    background: linear-gradient(90deg, #ffffff 10%, var(--cyan) 55%, var(--pink) 95%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    line-height: 1.1;
}
.vm-subtitle { color: var(--muted); font-size: 1.02rem; max-width: 640px; }

.vm-badges { margin-top: 1.1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.vm-badge {
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--ink);
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
}

/* Song cards */
.vm-card {
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.09);
    margin-bottom: 0.9rem;
    position: relative;
    overflow: hidden;
}
.vm-card::before {
    content: "";
    position: absolute; inset: 0 0 auto 0; height: 3px;
    background: linear-gradient(90deg, var(--pink), var(--cyan));
}
.vm-rank {
    display: inline-flex; align-items: center; justify-content: center;
    width: 1.9rem; height: 1.9rem; border-radius: 50%;
    background: linear-gradient(135deg, var(--pink), var(--purple));
    color: white; font-weight: 700; font-size: 0.85rem;
    margin-right: 0.6rem; flex-shrink: 0;
}
.vm-card-title { font-size: 1.12rem; font-weight: 700; color: var(--ink); }
.vm-card-artist { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.55rem; }
.vm-pill {
    display: inline-block; font-size: 0.72rem; font-weight: 600;
    padding: 0.16rem 0.55rem; border-radius: 999px; margin-right: 0.35rem;
    background: rgba(157,78,221,0.16); color: #d9b8ff; border: 1px solid rgba(157,78,221,0.4);
}
.vm-score { color: var(--cyan); font-weight: 700; font-size: 0.85rem; float: right; }
.vm-energy-track {
    height: 6px; border-radius: 999px; background: rgba(255,255,255,0.08);
    margin: 0.6rem 0 0.5rem 0; overflow: hidden;
}
.vm-energy-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--cyan), var(--pink)); }
.vm-reason { color: var(--muted); font-size: 0.83rem; margin: 0.2rem 0; }
.vm-note {
    margin-top: 0.6rem; font-size: 0.85rem; font-style: italic; color: #ffd7ea;
    border-left: 2px solid var(--pink); padding-left: 0.6rem;
}

/* Explanation / DJ quote panel */
.vm-explain {
    border-radius: 18px; padding: 1.3rem 1.5rem; margin: 1.1rem 0 1.4rem 0;
    background: linear-gradient(120deg, rgba(34,226,214,0.09), rgba(255,77,151,0.09));
    border: 1px solid rgba(255,255,255,0.1);
    color: var(--ink); font-size: 1.02rem; line-height: 1.55;
}
.vm-explain-label {
    font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--cyan); font-weight: 700; margin-bottom: 0.5rem; display: block;
}

/* Confidence meter */
.vm-conf-wrap { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.4rem; }
.vm-conf-track { flex: 1; height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
.vm-conf-fill { height: 100%; border-radius: 999px; }
.vm-conf-label { font-weight: 700; font-size: 0.95rem; white-space: nowrap; }

/* Trace timeline */
.vm-step {
    display: flex; gap: 0.7rem; padding: 0.55rem 0;
    border-bottom: 1px dashed rgba(255,255,255,0.08);
}
.vm-step:last-child { border-bottom: none; }
.vm-step-icon { font-size: 1.05rem; }
.vm-step-name { font-weight: 700; color: var(--ink); font-size: 0.9rem; }
.vm-step-detail { color: var(--muted); font-size: 0.83rem; margin-top: 0.1rem; }

.vm-footer { text-align: center; color: var(--muted); font-size: 0.82rem; margin-top: 2.2rem; padding-top: 1.2rem; border-top: 1px solid rgba(255,255,255,0.08); }
.vm-footer a { color: var(--cyan); text-decoration: none; }

div.stButton > button {
    border-radius: 999px; font-weight: 600; border: 1px solid rgba(255,77,151,0.5);
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def _load_catalog():
    return load_songs("data/songs.csv")


@st.cache_data
def _load_song_notes():
    return load_song_notes()


songs = _load_catalog()

EXAMPLES = [
    "chill lofi for late night coding",
    "upbeat pop for a workout",
    "something moody for a rainy commute, not too aggressive",
    "high energy dance music to get hyped",
]

if "vm_query" not in st.session_state:
    st.session_state.vm_query = ""
if "vm_result" not in st.session_state:
    st.session_state.vm_result = None
if "vm_last_query" not in st.session_state:
    st.session_state.vm_last_query = ""

# ---------------------------------------------------------------------------
# Sidebar -- what this is, for a recruiter skimming in 15 seconds
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎧 VibeMatch AI")
    st.caption("A content-based recommender wrapped in a RAG + agentic AI layer.")
    st.markdown(
        """
**How a request flows through the system:**

1. 🧠 **Parse** -- Claude turns free text into a structured taste profile
2. ✅ **Validate** -- guardrails clamp/sanitize before scoring
3. 🔍 **Retrieve** -- a deterministic scorer ranks the real catalog *(RAG)*
4. 🤔 **Critique** -- Claude self-checks the match & scores its own confidence
5. 🔄 **Re-retrieve** -- if confidence is low, it adjusts and tries again *(agentic loop)*
6. ✍️ **Explain** -- grounded in real catalog data + curator notes, never invented
        """
    )
    st.divider()
    st.markdown(
        "**Built with:** Claude (`claude-haiku-4-5`) · Python · Streamlit\n\n"
        "**Source:** [GitHub repo](https://github.com/shekinahokunbo/applied-ai-music-recommender)"
    )
    st.caption("Portfolio demo project -- 24-song fictional catalog, not a production system.")

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
<div class="vm-hero">
    <span class="vm-eyebrow">RAG &nbsp;+&nbsp; Agentic AI &nbsp;+&nbsp; Live Demo</span>
    <div class="vm-title">VibeMatch AI</div>
    <div class="vm-subtitle">Describe a mood, a moment, a vibe -- in your own words. An AI agent
    parses it, retrieves real songs from the catalog, critiques its own match, and explains
    its picks like it actually listened.</div>
    <div class="vm-badges">
        <span class="vm-badge">🧠 Claude-powered parsing</span>
        <span class="vm-badge">🔁 Self-critique &amp; re-retrieval</span>
        <span class="vm-badge">📚 Grounded in real catalog data</span>
        <span class="vm-badge">🎙️ Optional DJ persona</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

if not HAS_KEY:
    st.warning(
        "No `ANTHROPIC_API_KEY` is configured for this app, so requests will run in a "
        "degraded offline (keyword-matching) mode instead of using Claude. If this is your "
        "deployment, add the key under **Settings → Secrets**.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
st.markdown("#### What are you in the mood for?")

chip_cols = st.columns(len(EXAMPLES))
for col, example in zip(chip_cols, EXAMPLES):
    if col.button(example, use_container_width=True, key=f"chip_{example}"):
        st.session_state.vm_query = example

query = st.text_input(
    "Describe your vibe",
    key="vm_query",
    placeholder="e.g. 'moody synths for a late-night drive'",
    label_visibility="collapsed",
)

opt_col1, opt_col2 = st.columns([1, 3])
with opt_col1:
    persona = st.toggle("🎙️ Vibe the DJ persona", value=False)
with opt_col2:
    st.caption("Toggle a warm radio-host voice vs. a neutral factual explanation.")

go = st.button("✨ Find My Vibe", type="primary", use_container_width=False)

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
if go and query.strip():
    with st.spinner("Spinning through the crates..."):
        try:
            result = run_pipeline(query, songs, persona=persona)
        except Exception as exc:  # noqa: BLE001 -- surfaced to the user, not swallowed
            result = None
            st.error(f"Something went wrong while generating recommendations: {exc}")
    st.session_state.vm_result = result
    st.session_state.vm_last_query = query
elif go:
    st.info("Type a vibe first -- try one of the chips above.")

result = st.session_state.vm_result

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if result:
    if result.get("rejected"):
        st.info(result["explanation"])
    else:
        if result.get("degraded"):
            st.info(
                "The Claude API wasn't reachable for this request, so it fell back to "
                "offline keyword matching (reliability guardrail, not a crash).",
                icon="🛟",
            )

        confidence = result.get("confidence")
        if confidence is not None:
            pct = max(0.0, min(1.0, confidence)) * 100
            color = "#22e2d6" if confidence >= 0.7 else ("#ffd166" if confidence >= 0.5 else "#ff4d97")
            st.markdown(
                f"""
<div class="vm-conf-wrap">
    <div class="vm-conf-track"><div class="vm-conf-fill" style="width:{pct:.0f}%; background:{color};"></div></div>
    <div class="vm-conf-label" style="color:{color};">{confidence:.2f} confidence</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
<div class="vm-explain">
    <span class="vm-explain-label">{"🎙️ Vibe the DJ says" if persona else "AI explanation"}</span>
    {result["explanation"]}
</div>
""",
            unsafe_allow_html=True,
        )

        recs = result.get("recommendations", [])
        notes_map = _load_song_notes()
        left, right = st.columns(2)
        for i, (song, score, why) in enumerate(recs):
            target = left if i % 2 == 0 else right
            energy_pct = max(0.0, min(1.0, float(song.get("energy", 0)))) * 100
            note_text = notes_map.get(str(song.get("id")))
            note_html = f'<div class="vm-note">"{note_text}"</div>' if note_text else ""

            target.markdown(
                f"""
<div class="vm-card">
    <span class="vm-score">score {score:.2f}</span>
    <span class="vm-rank">{i + 1}</span>
    <span class="vm-card-title">{song['title']}</span>
    <div class="vm-card-artist">by {song['artist']}</div>
    <span class="vm-pill">{song['genre']}</span>
    <span class="vm-pill">{song['mood']}</span>
    <div class="vm-energy-track"><div class="vm-energy-fill" style="width:{energy_pct:.0f}%;"></div></div>
    <div class="vm-reason">{why}</div>
    {note_html}
</div>
""",
                unsafe_allow_html=True,
            )

        with st.expander("🔬 See how the agent thought about this"):
            step_icons = {
                "guardrail": "🚧",
                "parse": "🧠",
                "validate": "✅",
                "retrieve": "🔍",
                "critique": "🤔",
                "re-retrieve": "🔄",
                "explain": "✍️",
            }
            for step in result["trace"]:
                name = step.get("step", "step")
                icon = step_icons.get(name, "•")
                detail = {k: v for k, v in step.items() if k != "step"}
                st.markdown(
                    f"""<div class="vm-step"><div class="vm-step-icon">{icon}</div>
                    <div><div class="vm-step-name">{name}</div>
                    <div class="vm-step-detail">{detail}</div></div></div>""",
                    unsafe_allow_html=True,
                )

st.markdown(
    """
<div class="vm-footer">
    VibeMatch AI is a portfolio project demonstrating RAG, agentic self-critique, and
    persona-specialized prompting on top of a transparent, hand-built recommender.
    &nbsp;·&nbsp; <a href="https://github.com/shekinahokunbo/applied-ai-music-recommender" target="_blank">View source on GitHub</a>
</div>
""",
    unsafe_allow_html=True,
)
