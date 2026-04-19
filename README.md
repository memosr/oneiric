# Oneiric

> **Turn your voice-recorded dreams into surreal Dalí-style short films.**

Built on **[Hermes Agent](https://nous.systems)** by Nous Research · Powered by **Kimi K2.5**

[![Hackathon](https://img.shields.io/badge/Nous%20Research-Hackathon%202026-blueviolet)](https://nous.systems)
[![Model](https://img.shields.io/badge/Model-Kimi%20K2.5-blue)](https://kimi.ai)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)]()
[![Last Commit](https://img.shields.io/github/last-commit/memosr/oneiric)](https://github.com/memosr/oneiric/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/memosr/oneiric)](https://github.com/memosr/oneiric)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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
      ▼
4. NARRATE      — Dream Composer skill writes and voices cinematic narration via OpenAI TTS
      │
      ▼
5. COMPOSE      — FFmpeg assembles frames + narration into a short film (.mp4)
      │
      ▼
  Gallery (Next.js) — Browse and share your dream films
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
| Video assembly | FFmpeg |
| Gallery frontend | Next.js + Tailwind CSS |
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
│transcribe│──→│ analyze │──→│illustrate│──→│ narrate │──→│ compose  │
│  planned │   │  done   │   │  done    │   │  done   │   │ planned  │
└──────────┘   └─────────┘   └──────────┘   └─────────┘   └──────────┘
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

### Next (Day 4+)
- Extend `narrate.py` to also speak the raw transcript (dual-narrator film)
- `pipeline/compose.py` — FFmpeg-based video assembly: Ken Burns scene motion,
  scene description subtitles, dual-track audio (transcript + Jungian reading)
- `pipeline/transcribe.py` — voice note → Turkish text (Whisper via Hermes)
- `pipeline/main.py` — end-to-end orchestrator
- Next.js gallery for dream archive
- Demo video + hackathon submission

---

## Live Example: Dream #001

**Title (pipeline):** *Divided Tree of Self*
**Mood:** foreboding
**Symbols:** fruit tree, baby snake, daughter, division, work

See the full archive at [`gallery/public/dreams/dream_001/`](gallery/public/dreams/dream_001/):
- `manual_run/` — first Telegram-orchestrated attempt (2/3 scenes)
- `pipeline_run/` — first programmatic attempt (3/3 scenes, 16:9)
- `pipeline_run_v2/` — vertical 9:16 regeneration for mobile video (3/3 scenes)

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
