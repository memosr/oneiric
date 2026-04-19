"""Stage 2: Analyze — Hermes + Kimi K2.5 dream transcript → structured JSON."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

_ANALYSIS_PROMPT_TEMPLATE = """\
You are a Jungian dream analyst. Analyze the following dream transcript and return ONLY a valid JSON object — no markdown, no explanation, no extra text.

The transcript may be in Turkish. Analyze it carefully.

Return this exact JSON schema:
{{
  "title": "<English 2-5 word artistic title>",
  "scenes": [
    {{
      "order": <int, 1-based>,
      "description": "<English cinematic scene description, 2-3 sentences>"
    }}
  ],
  "symbols": ["<symbol1>", "<symbol2>"],
  "mood": "<single English word>",
  "color_palette": ["<#hex>", "<#hex>", "<#hex>", "<#hex>"],
  "jungian_reading_tr": "<Turkish Jungian interpretation, 3-4 sentences>"
}}

Rules:
- scenes count: 2-3 for short transcripts, 4-5 for long ones
- color_palette: exactly 4 hex colors matching the dream's emotional tone
- mood: single lowercase English word
- title: 2-5 words, evocative and artistic
- jungian_reading_tr: written in Turkish, Jungian style

Dream transcript:
{transcript}

Respond with the JSON object only."""


def _call_hermes(prompt: str) -> str:
    """Run `hermes chat -q <prompt>` and return raw stdout."""
    result = subprocess.run(
        ["hermes", "chat", "-q", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Hermes exited with code {result.returncode}.\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result.stdout


def _extract_json(raw: str) -> str:
    """Extract the outermost JSON object from Hermes TUI output.

    Hermes outputs a splash screen, then echoes the query (which may contain
    JSON schema placeholders), then shows the model response after a
    '⚕ Hermes' separator line. We skip to after that separator before
    searching for the first '{'.
    """
    # Find the response section — it starts after the '⚕ Hermes' header line.
    hermes_marker = raw.find("⚕ Hermes")
    search_start = (hermes_marker + len("⚕ Hermes")) if hermes_marker != -1 else 0

    start = raw.find("{", search_start)
    if start == -1:
        raise ValueError("No '{' found in Hermes response section")

    # Walk forward tracking brace depth to find the matching '}'
    depth = 0
    end = start
    in_string = False
    escape_next = False
    for i, ch in enumerate(raw[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    return raw[start : end + 1]


def _clean_tui_json(text: str) -> str:
    """Fix JSON that was word-wrapped by Hermes TUI formatting.

    The TUI renders content in a fixed-width box, inserting literal newlines
    inside JSON string values. This function replaces those newlines (and any
    surrounding whitespace) with a single space, while preserving intentional
    structure newlines between JSON tokens.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    joined = "\n".join(lines)

    # Walk character-by-character; inside a quoted string, replace \n with space.
    result = []
    in_string = False
    escape_next = False
    skip_whitespace = False
    for ch in joined:
        if escape_next:
            escape_next = False
            result.append(ch)
            continue
        if ch == "\\" and in_string:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if ch == "\n" and in_string:
            # Collapse TUI line break + following indent into a single space.
            if result and result[-1] != " ":
                result.append(" ")
            skip_whitespace = True
            continue
        if skip_whitespace:
            if ch == " ":
                continue
            skip_whitespace = False
        result.append(ch)
    return "".join(result)


def _parse_json(text: str, raw_output: str) -> dict:
    """Extract and parse JSON from Hermes output."""
    try:
        json_str = _extract_json(raw_output)
    except ValueError as exc:
        raise RuntimeError(
            f"Could not locate JSON in Hermes response: {exc}\n"
            f"--- raw output (first 2000 chars) ---\n{raw_output[:2000]}"
        ) from exc

    cleaned = _clean_tui_json(json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse JSON from Hermes response: {exc}\n"
            f"--- extracted JSON ---\n{json_str}\n"
            f"--- cleaned JSON ---\n{cleaned}\n"
            f"--- raw output (first 2000 chars) ---\n{raw_output[:2000]}"
        ) from exc


def _validate_schema(data: dict) -> None:
    """Light schema check — raise RuntimeError if required keys are missing."""
    required = {"title", "scenes", "symbols", "mood", "color_palette", "jungian_reading_tr"}
    missing = required - data.keys()
    if missing:
        raise RuntimeError(f"Analysis JSON missing required keys: {missing}")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) == 0:
        raise RuntimeError("'scenes' must be a non-empty list")
    if not isinstance(data["color_palette"], list) or len(data["color_palette"]) != 4:
        raise RuntimeError("'color_palette' must be a list of exactly 4 hex strings")


def analyze_dream(
    transcript: str,
    dream_id: str | None = None,
    output_path: Path | None = None,
) -> dict:
    """
    Analyze a Turkish dream transcript using Hermes + Kimi K2.5.

    Args:
        transcript: Raw dream transcript (Turkish text)
        dream_id: Optional ID for the dream (e.g., "dream_002")
        output_path: Optional path to write the JSON output

    Returns:
        Dict matching the analysis schema

    Raises:
        RuntimeError if Hermes call fails or returns invalid JSON
    """
    prompt = _ANALYSIS_PROMPT_TEMPLATE.format(transcript=transcript.strip())

    raw_output = _call_hermes(prompt)
    result = _parse_json(raw_output, raw_output)
    _validate_schema(result)

    if dream_id is not None:
        result["id"] = dream_id
        result["date"] = date.today().isoformat()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Analyze a dream transcript with Hermes.")
    ap.add_argument("--transcript", required=True, help="Path to a .txt file containing the transcript")
    ap.add_argument("--dream-id", default=None)
    ap.add_argument("--output", default=None, help="Path to write JSON output")
    args = ap.parse_args()

    transcript_text = Path(args.transcript).read_text(encoding="utf-8")
    result = analyze_dream(
        transcript_text,
        args.dream_id,
        Path(args.output) if args.output else None,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
