# Oneiric — Technical Architecture

## Overview

Oneiric is a Hermes Agent-orchestrated pipeline that converts a voice recording into a short film. The agent maintains persistent state across the 5-stage pipeline and delegates to specialized skills via Hermes tool calls.

```
Audio (.m4a/.wav)
       │
  pipeline/main.py  ←── Hermes Agent (Kimi K2.5)
       │                       │
       ├── transcribe.py       ├── tool: whisper_transcribe
       ├── analyze.py          ├── skill: dream-analyst
       ├── illustrate.py       ├── skill: dream-illustrator (tool: fal_generate)
       ├── narrate.py          ├── skill: dream-composer (tool: openai_tts)
       └── compose.py          └── tool: ffmpeg_compose
```

---

## Pipeline Stages

### 1. `pipeline/transcribe.py`
**Purpose:** Convert raw audio to text using OpenAI Whisper.

- **Input:** `audio_path: str` — path to .m4a / .wav / .mp3
- **Output:** `transcript: str` — raw spoken dream text
- **Hermes tool:** `whisper_transcribe(audio_path) → {text, language, segments}`
- **Notes:** Segments are preserved for timing data used later by FFmpeg.

---

### 2. `pipeline/analyze.py`
**Purpose:** Extract structured dream metadata from the transcript.

- **Input:** `transcript: str`
- **Output:** `DreamAnalysis` — structured object:
  ```json
  {
    "title": "The Glass Cathedral",
    "mood": "melancholic",
    "symbols": ["clock", "ocean", "mirror"],
    "narrative_arc": ["arrival", "dissolution", "awakening"],
    "color_palette": ["cerulean", "burnt sienna", "bone white"],
    "visual_motifs": ["melting architecture", "infinite corridors"],
    "narration_style": "third-person poetic"
  }
  ```
- **Hermes skill:** `dream-analyst` — runs as a subagent with its own SOUL.md
- **Notes:** Symbol extraction is the most critical step; quality here propagates through the entire pipeline.

---

### 3. `pipeline/illustrate.py`
**Purpose:** Generate Dalí-style image frames from visual motifs.

- **Input:** `DreamAnalysis` — symbols, palette, motifs
- **Output:** `frames: list[str]` — paths to generated .png files
- **Hermes skill:** `dream-illustrator`
- **Hermes tool:** `fal_generate(prompt, style_lora, aspect_ratio) → {image_url}`
- **Prompt strategy:** Each symbol/motif becomes a separate FAL call with a shared Dalí style prefix: `"surrealist oil painting, Salvador Dalí style, dreamlike, {motif}, {palette}"`
- **Frame count:** 5–8 frames per dream (configurable)

---

### 4. `pipeline/narrate.py`
**Purpose:** Write and voice cinematic narration for the dream film.

- **Input:** `DreamAnalysis`, `transcript`
- **Output:** `narration_audio: str` — path to .mp3
- **Hermes skill:** `dream-composer`
- **Hermes tool:** `openai_tts(text, voice="onyx") → {audio_path}`
- **Notes:** Narration is rewritten from transcript in the `narration_style` specified by the analyst. Target length: 60–90 seconds.

---

### 5. `pipeline/compose.py`
**Purpose:** Assemble frames and narration into a short film.

- **Input:** `frames: list[str]`, `narration_audio: str`, `segments: list`
- **Output:** `film_path: str` — path to final .mp4
- **Hermes tool:** `ffmpeg_compose(frames, audio, output_path, duration_per_frame)`
- **FFmpeg strategy:** Ken Burns pan/zoom effect per frame, crossfade transitions, narration audio overlaid, ambient texture optionally mixed from `assets/ambient/`.

---

## State Management

Hermes persists pipeline state in `.hermes-cache/` (gitignored). If the pipeline fails at stage 3, rerunning `main.py` with the same dream ID resumes from stage 3 — the transcript and analysis are loaded from memory.

Each dream is assigned a UUID at intake. State is keyed by this ID.

---

## Gallery

A Next.js frontend in `gallery/` reads `gallery/data/dreams.json` and serves the generated films. Each entry in the JSON array:

```json
{
  "id": "uuid",
  "title": "The Glass Cathedral",
  "created_at": "2026-04-18T10:00:00Z",
  "mood": "melancholic",
  "film_url": "/dreams/uuid.mp4",
  "thumbnail_url": "/dreams/uuid_thumb.jpg",
  "symbols": ["clock", "ocean", "mirror"]
}
```

---

## Hermes Config

`hermes/config/config.yaml` controls:
- Model selection (default: `kimi-k2.5`)
- API keys (loaded from environment)
- FAL style LoRA path
- FFmpeg output settings (resolution, fps, codec)
- Gallery output directory

---

## Lessons Learned

### 2026-04-19 — Manual Telegram orchestration fails silently

**What we tried:** Asked Hermes via Telegram to generate all 3 scene images in a single multi-step conversation (analyze → plan → illustrate × 3).

**What happened:** Scene 2 was silently dropped. Hermes returned no error — it simply moved to scene 3 after "finishing" scene 1. A later single-scene retry produced a FAL URL that 404'd when opened.

**Why it matters:** Multi-step agentic chat is non-deterministic. A failed tool call inside a chain can be swallowed. For a production pipeline where every scene matters, we cannot trust the agent to self-heal.

**The pivot:** Pipeline stages will be invoked programmatically from Python, each stage isolated, each call retried on failure, each artifact validated before the next stage begins. Telegram remains only as input (voice note intake) and output (final film delivery) — not orchestration.

### 2026-04-19 (evening) — Pipeline vindicates the pivot

**What we tried:** Wrote `illustrate.py` with per-scene isolation, retry logic, and immediate download of FAL URLs.

**What happened:** First invocation returned 0/3 images — the Hermes TUI was wrapping long URLs across two lines and the initial regex missed them. After adding a "slow path" that strips/joins whitespace before URL extraction, the retry loop recovered and completed 3/3.

**Why it matters:** The same class of bug that killed scene 2 in manual mode (silent tool failure) was caught, diagnosed, and fixed automatically by the pipeline. Manual chat hides failures; programmatic pipelines expose them.

**The payoff:** Three consistent Dalí-style images generated in ~2 minutes, end-to-end. Dream #001 now has both a manual run (partial) and a pipeline run (complete) archived side-by-side as proof of the pivot's value.
