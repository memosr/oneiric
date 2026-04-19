# Next Session

## Priority 1 — Extend narrate.py
- Add a `narrate_transcript()` helper so the raw dream transcript (Turkish)
  becomes an audio file alongside `narration.mp3`
- Output: `transcript_narration.mp3` in the same output dir
- Update `narrate_dream()` to generate both
- Re-run on Dream #001 to produce dual audio files

## Priority 2 — compose.py (FFmpeg film assembly)
- Input: analysis JSON + pipeline_run_v2 scene images + both mp3s
- Pipeline:
  - Title card (3 sec): `title` centered, serif font, fade in/out
  - Scenes: each image ~8-10 sec with Ken Burns (zoompan filter, slow pan)
  - Scene description subtitle at bottom during each scene (English)
  - Transcript narration plays during the first pass of scenes
  - Short beat (2 sec) after transcript ends
  - Scenes replay slightly slower; Jungian narration plays
  - End card (3 sec): Oneiric watermark
- Output: 9:16 MP4, 1080x1920 (upscaled from 576x1024) or native 576x1024
- FFmpeg reference filters: zoompan, drawtext, xfade, amix

## Priority 3 — Dogfood
- Run the full pipeline on a second dream (collect one tonight or tomorrow)
- Archive as Dream #002
- Verify nothing regresses

## Open questions
- Upscale images to 1080x1920 for video quality? (waifu2x or nearest-neighbor)
- Font choice for subtitles and title card (Playfair Display? Cormorant Garamond?)
- Ambient music — add after MVP?
