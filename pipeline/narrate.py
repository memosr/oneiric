"""Stage 4: Narrate — Jungian interpretation TTS via Hermes → MP3."""

from __future__ import annotations

import glob as _glob
import json
import os
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

_MEDIA_RE = re.compile(r'MEDIA:(\S+\.mp3)')


def _call_hermes(text: str, timeout: int) -> str:
    # json.dumps produces a properly escaped string literal (handles ', ", \n, etc.)
    # Strip outer quotes, then escape remaining single quotes for shell embedding.
    escaped = json.dumps(text)[1:-1].replace("'", "\\'")
    prompt = (
        f"Use the text_to_speech tool EXACTLY ONCE to speak this Turkish text: "
        f"'{escaped}' "
        f"After the audio is generated, respond with ONLY the media path and "
        f"nothing else — no commentary, no markdown, no explanation."
    )
    result = subprocess.run(
        ["hermes", "chat", "-q", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Hermes exited {result.returncode}. stderr: {result.stderr.strip()}"
        )
    return result.stdout


def _extract_media_path(raw: str) -> str | None:
    """Find MEDIA:<path>.mp3 in Hermes TUI output after the response separator."""
    hermes_marker = raw.find("⚕ Hermes")
    search_start = (hermes_marker + len("⚕ Hermes")) if hermes_marker != -1 else 0
    response_section = raw[search_start:]

    m = _MEDIA_RE.search(response_section)
    if m:
        return m.group(1)

    # Fallback: strip TUI line-wrapping and retry
    compact = "".join(line.strip() for line in response_section.splitlines())
    m = _MEDIA_RE.search(compact)
    return m.group(1) if m else None


def _resolve_cache_path(reported_path: str) -> str | None:
    """Return the actual on-disk path for a Hermes-reported MEDIA path.

    Hermes has a known bug where it reports the wrong year in the filename
    (e.g. tts_20250419_... instead of tts_20260419_...). If the exact path
    doesn't exist, we try replacing the embedded year with today's year and
    also search the cache dir for a file whose name ends with the same
    timestamp suffix (MMDD_HHMMSS.mp3).
    """
    if os.path.exists(reported_path):
        return reported_path

    p = Path(reported_path)
    # Try correcting just the year (handles the off-by-one-year Hermes bug)
    corrected = str(p.parent / p.name.replace(
        str(date.today().year - 1), str(date.today().year), 1
    ))
    if os.path.exists(corrected):
        return corrected

    # Last resort: find any file in the same dir with the same MMDDHHMMSS suffix
    suffix_match = re.search(r'tts_\d{4}(\d{8}\.mp3)$', p.name)
    if suffix_match:
        pattern = str(p.parent / f"tts_*{suffix_match.group(1)}")
        candidates = _glob.glob(pattern)
        if candidates:
            return max(candidates, key=os.path.getmtime)

    return None


def narrate_text(
    text: str,
    output_path: Path,
    max_retries: int = 3,
    timeout: int = 120,
) -> dict:
    """
    Convert Turkish text to speech via Hermes TTS tool, copy resulting
    mp3 to output_path.

    Returns:
        {
          "status": "success" | "failed",
          "text": <first 100 chars>,
          "cache_path": <original Hermes path> | None,
          "output_path": str,
          "attempts": int,
          "error": str | None,
          "duration_sec": float,
          "file_size_bytes": int | None,
        }

    Never raises. Failure is a valid result state.
    """
    output_path = Path(output_path)
    result: dict = {
        "status": "failed",
        "text": text[:100],
        "cache_path": None,
        "output_path": str(output_path),
        "attempts": 0,
        "error": None,
        "duration_sec": 0.0,
        "file_size_bytes": None,
    }

    t0 = time.monotonic()

    for attempt in range(1, max_retries + 1):
        result["attempts"] = attempt
        try:
            raw = _call_hermes(text, timeout)
            cache_path = _extract_media_path(raw)

            if not cache_path:
                result["error"] = f"Attempt {attempt}: no MEDIA path found in output"
                continue

            resolved = _resolve_cache_path(cache_path)
            if not resolved:
                result["error"] = (
                    f"Attempt {attempt}: MEDIA path not found on disk: {cache_path}"
                )
                continue

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved, output_path)
            cache_path = resolved

            file_size = output_path.stat().st_size
            if file_size < 1024:
                result["error"] = (
                    f"Attempt {attempt}: copied file too small ({file_size} bytes)"
                )
                continue

            result["status"] = "success"
            result["cache_path"] = cache_path
            result["file_size_bytes"] = file_size
            result["error"] = None
            break

        except subprocess.TimeoutExpired:
            result["error"] = f"Attempt {attempt}: Hermes timed out after {timeout}s"
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"Attempt {attempt}: {exc}"

    result["duration_sec"] = round(time.monotonic() - t0, 2)
    return result


def narrate_dream(
    analysis: dict,
    output_dir: Path,
) -> dict:
    """
    Narrate the jungian_reading_tr of a dream analysis.
    Writes to: output_dir / 'narration.mp3'

    Args:
        analysis: Dict returned by analyze_dream(), must contain
                  'jungian_reading_tr' key
        output_dir: Directory to write narration.mp3 to

    Returns:
        Result dict from narrate_text() plus 'analysis_excerpt'
        (first 100 chars of narrated text) for logging.
    """
    text = analysis["jungian_reading_tr"]
    output_path = Path(output_dir) / "narration.mp3"
    result = narrate_text(text, output_path)
    result["analysis_excerpt"] = text[:100]
    return result


def narrate_dream_full(
    analysis: dict,
    output_dir: Path,
    transcript_fallback: str | None = None,
) -> dict:
    """
    Narrate both the raw transcript AND the Jungian interpretation.
    Produces two mp3 files:
      - transcript_narration.mp3 (analysis["transcript_tr"] or transcript_fallback)
      - jungian_narration.mp3    (analysis["jungian_reading_tr"])

    Returns:
        {
          "transcript": <result dict from narrate_text, or {"status": "skipped"}>,
          "jungian":    <result dict from narrate_text>,
          "success_count": <0, 1, or 2>,
        }
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_text = analysis.get("transcript_tr") or transcript_fallback
    if transcript_text:
        transcript_result = narrate_text(
            transcript_text,
            output_dir / "transcript_narration.mp3",
        )
    else:
        transcript_result = {"status": "skipped", "reason": "no transcript_tr in analysis and no fallback provided"}

    jungian_result = narrate_text(
        analysis["jungian_reading_tr"],
        output_dir / "jungian_narration.mp3",
    )

    success_count = sum(
        1 for r in (transcript_result, jungian_result)
        if r.get("status") == "success"
    )

    return {
        "transcript": transcript_result,
        "jungian": jungian_result,
        "success_count": success_count,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Narrate a dream's Jungian interpretation.")
    ap.add_argument("--analysis", required=True, help="Path to analysis JSON from analyze.py")
    ap.add_argument("--output-dir", required=True, help="Directory to write narration file(s) to")
    ap.add_argument("--full", action="store_true",
                    help="Narrate both transcript and Jungian reading")
    ap.add_argument("--transcript-from-file", metavar="PATH",
                    help="Fallback transcript text file (used when analysis lacks transcript_tr)")
    args = ap.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))

    if args.full:
        fallback = None
        if args.transcript_from_file:
            fallback = Path(args.transcript_from_file).read_text(encoding="utf-8").strip()
        result = narrate_dream_full(analysis, Path(args.output_dir), transcript_fallback=fallback)
    else:
        result = narrate_dream(analysis, Path(args.output_dir))

    print(json.dumps(result, indent=2, ensure_ascii=False))
