# Oneiric

> **Turn your voice-recorded dreams into surreal Dalí-style dream cards.**

Built on **[Hermes Agent](https://nous.systems)** by Nous Research · Powered by **Kimi K2.5**

[![Hackathon](https://img.shields.io/badge/Nous%20Research-Hackathon%202026-blueviolet)](https://nous.systems)
[![Model](https://img.shields.io/badge/Model-Kimi%20K2.5-blue)](https://kimi.ai)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)]()
[![Last Commit](https://img.shields.io/github/last-commit/memosr/oneiric)](https://github.com/memosr/oneiric/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/memosr/oneiric)](https://github.com/memosr/oneiric)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live](https://img.shields.io/badge/🌐_Live-oneiric--zeta.vercel.app-6b46c1?style=flat)](https://oneiric-zeta.vercel.app)

---

## The Problem

Dreams are ephemeral. Within 10 minutes of waking, most people forget 90% of what they dreamed. Even when fragments survive, translating the strange, shifting logic of a dream into something visual or sharable is nearly impossible — language falls short, and most people lack the artistic tools to try.

Dreams are the most cinematic experiences we have, yet they vanish without a trace.

---

## How It Works

Oneiric runs a 5-stage pipeline orchestrated by a Hermes Agent:

```
Voice Recording
      │
      ▼
1. TRANSCRIBE   — Whisper converts spoken dream narration to raw text
      │
      ▼
2. ANALYZE      — Dream Analyst skill extracts symbols, emotions, narrative arcs
      │
      ▼
3. ILLUSTRATE   — Dream Illustrator skill generates Dalí-style frames via FAL API
      │
      ├──→ 4. CARD     — Pillow assembles scenes + transcript + Jungian chips into
      │                   a 1080x1920 dream card PNG  [PRIMARY OUTPUT]
      │
      └──→ 4b. NARRATE → 5. COMPOSE  — dual-mp3 narration + FFmpeg film assembly
                                        [BONUS OUTPUT — optional]
      │
      ▼
  Gallery (HTML + Tailwind) — Scrollable card grid, Vercel deploy
```

Each stage is a discrete Hermes skill, allowing the agent to delegate, retry, and persist intermediate state across sessions.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent runtime | [Hermes Agent](https://nous.systems) (Nous Research) |
| LLM backbone | Kimi K2.5 |
| Speech-to-text | OpenAI Whisper |
| Image generation | FAL API (Flux / SDXL with Dalí style LoRA) |
| Text-to-speech | OpenAI TTS (onyx voice) |
| Card rendering | Pillow (PIL) — gradient generation, typography, image compositing |
| Typography | Playfair Display — serif titles and body text |
| Translation | Kimi K2.5 — Turkish → English for symbol chips and Jungian readings |
| Video assembly | FFmpeg — film assembly (bonus/optional output) |
| Gallery frontend | Plain HTML + Tailwind CDN (Vercel static deploy) |
| Storage | Local filesystem / S3-compatible |

---

## Why Hermes

Oneiric leans on Hermes Agent's three core superpowers:

**Persistent Memory** — Dream analysis state is stored across sessions. If the pipeline fails mid-way, the agent resumes from where it left off, preserving symbol maps and emotional arcs already extracted.

**Subagent Delegation** — The orchestrator delegates to three specialized skills (`dream-analyst`, `dream-illustrator`, `dream-composer`) rather than doing everything in one giant prompt. Each skill has its own context, tools, and failure surface.

**Tool Gateway** — FAL, Whisper, TTS, and FFmpeg are all exposed as Hermes tools with typed inputs/outputs, retry logic, and structured error handling. The agent decides when and how to call each tool based on pipeline state.

---

## Progress

```
┌──────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
│transcribe│──→│ analyze │──→│illustrate│──→│  card   │──→│ gallery  │
│ planned  │   │  done   │   │  done    │   │  done   │   │   done   │
└──────────┘   └─────────┘   └──────────┘   └─────────┘   └──────────┘
                                    │
                                    ├──→ narrate ──→ compose (film, bonus)
                                    │      done        done
```

### Day 1 — 2026-04-18
- Hermes Agent (v0.10.0) installed, configured with Kimi K2.5 via Nous Portal
- Tool Gateway enabled (FAL image, OpenAI TTS, Firecrawl web, Browser Use)
- Telegram gateway wired to a dedicated bot (`@UyandikBot`)
- GitHub repo scaffolded with placeholder pipeline files

### Day 2 — 2026-04-19 (morning)
- First real dream recorded via Telegram voice note (Dream #001)
- Manual Telegram orchestration tested — revealed silent tool-call skipping
- Pivoted from chat-based orchestration to a programmatic Python pipeline
- `pipeline/analyze.py` implemented — Hermes subprocess → Kimi K2.5 →
  structured JSON analysis with Jungian interpretation in Turkish

### Day 3 — 2026-04-19 (afternoon)
- `pipeline/illustrate.py` — per-scene FAL image generation with retry logic
  (3/3 scene consistency achieved on Dream #001)
- Switched default image generation to 9:16 vertical for mobile-first video
- `pipeline/narrate.py` — TTS narration of the Jungian interpretation
  (832 KB Turkish audio, first-attempt success)
- Three archived runs of Dream #001 preserved side-by-side as evidence of
  iteration: `manual_run`, `pipeline_run`, `pipeline_run_v2`

### Day 4 — 2026-04-20
- Extended `narrate.py` with dual-narrator mode (transcript + Jungian reading), producing two mp3s per dream
- `pipeline/compose.py` — FFmpeg-based 9:16 video assembly with Ken Burns, drawtext subtitles, dual audio mixing. Two test films rendered (Dream #001 and Dream #002), ~70-100s each.
- **Pivot:** Film output had polish hurdles (Ken Burns timing, subtitle layout, render cost per iteration). Decided the primary deliverable should be a **dream card** — a single high-resolution PNG combining scenes, transcript, Jungian interpretation, and metadata chips. Film mode remains as a bonus capability.
- `pipeline/card.py` — 1080x1920 dream card generator with dynamic palette gradient (per-dream), English transcript excerpt, translated Jungian summary, symbol chips, Playfair Display typography.
- **Polish pass:** 6 fixes landed in a single commit (English symbol chips, full-height layout, smart truncation at sentence boundaries, synthetic gradient for palettes lacking dark variants, contrast-aware chip text coloring, two-line footer).
- **Dream #003 — *Keys Without Locks* (fictional).** Stress test: absurd cross-species metamorphoses (fish-as-books, chess-knight librarian, key rain). Kimi autonomously produced 4 scenes for this richer dream (pipeline supports 2-5 dynamically). Card shows first 3; scene 4 archived as bonus with provenance notes.
- Three-dream gallery complete, spanning three Jungian archetypes: **Shadow · Self · Trickster**.

### Day 5 — 2026-04-24

- **Telegram automation complete:** `@OneiricDreamBot` listens for text
  dreams and runs the full pipeline end-to-end. Card arrives back as a
  photo in 3-5 minutes. First real-world test: 5 new dreams archived
  automatically (Dreams #004 through #008), spanning moods from
  ethereal to whimsical to luminous.
- **pipeline/main.py** — end-to-end orchestrator (transcript → analyze →
  illustrate → card → dream.json → dreams.json update)
- **pipeline/listener.py** — python-telegram-bot v22 daemon with allowlist,
  async pipeline invocation, error-safe card delivery
- **Gallery normalized:** `dreams.json` schema unified across all 8 dreams
  (thumbnail: card.png, dreamer, archetype, mood for every entry)
- **Static HTML gallery** (`gallery/index.html` + `script.js`): responsive
  grid, lightbox modal, Playfair Display typography, mobile-first
- **Live on Vercel:** `oneiric-zeta.vercel.app`. GitHub push triggers
  automatic redeploy, so the gallery grows with every new dream sent to
  the bot.
- **Three archetypes × five moods on the gallery:** shadow, self,
  trickster, anima, puer.

### Next (Day 6+)
- Demo video (2 min) for hackathon submission — storyboard, screen capture,
  voiceover, final grid reveal
- Invite friends to @OneiricDreamBot — real-world user testing, collect
  dream cards from others
- Extend card.py to support 4-5 scene layouts (Dream #003 has a bonus
  scene #4 archived but unused in its card)
- X (Twitter) post draft tagging @NousResearch + Discord submission to
  `creative-hackathon-submissions` channel
- Polish & buffer days — May 1-3

---

## 🌐 Live Gallery

**[oneiric-zeta.vercel.app](https://oneiric-zeta.vercel.app)**

Browse the full dream archive — 8 cards in a responsive 9:16 grid with
lightbox. Mobile-first. Auto-deploys on every new dream via the
Telegram pipeline.

**Try it:** send a dream as text to
**[@OneiricDreamBot](https://t.me/OneiricDreamBot)** on Telegram.
Your card arrives in 3-5 minutes, gallery updates automatically
on next git push.

---

## Live Examples

### Dream #001 — *The Divided Tree of Consciousness*
- **Mood:** foreboding · **Archetype:** shadow
- **Symbols:** fruit tree, baby snake, duality, paternal protection
- Three archived runs: [`manual_run`](gallery/public/dreams/dream_001/manual_run/) (2/3, Telegram), [`pipeline_run`](gallery/public/dreams/dream_001/pipeline_run/) (3/3, 16:9), [`pipeline_run_v2`](gallery/public/dreams/dream_001/pipeline_run_v2/) (3/3, 9:16)

### Dream #002 — *Sacred Thresholds of the Soul*
- **Mood:** transcendent · **Archetype:** self
- **Symbols:** yeşillik, dua, manevi belde, aile sofrası
- [`pipeline_run`](gallery/public/dreams/dream_002/pipeline_run/) — 3/3 scenes, all first-attempt success, pure programmatic pipeline

### Dream #003 — *Keys Without Locks* (fictional)
- **Mood:** liminal · **Archetype:** trickster
- **Symbols:** fish, library, chess knight, keys, locks
- [`pipeline_run`](gallery/public/dreams/dream_003/pipeline_run/) — 4/4 scenes generated (card shows 3, scene 4 archived as bonus)
- Stress test: absurd cross-species metamorphoses (fish-books, chess-knight-librarian). Pipeline autonomously produced 4 scenes for this richer dream.

**Why three dreams?** Each card represents a distinct Jungian archetype — Dream #001 (Shadow: a baby serpent lurking), Dream #002 (Self: luminous spiritual realms), Dream #003 (Trickster: fish-as-books, chess-knight librarian). The same pipeline — no prompt tuning — produced all three with atmosphere faithful to each dream's emotional register. That is the core claim of Oneiric: your dream's feeling determines the card's face.

---

## Getting Started

```bash
# Clone
git clone https://github.com/memosr/oneiric.git
cd oneiric

# Python pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp hermes/config/config.yaml.example hermes/config/config.yaml
# Edit config.yaml with your API keys

# Run
python pipeline/main.py --audio my_dream.m4a
```

---

## Author

**memosr** — building at the intersection of memory, consciousness, and generative AI.

---

*Submitted to the Nous Research Hackathon · Deadline: May 3, 2026*
