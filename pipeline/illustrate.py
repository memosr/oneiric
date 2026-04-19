# Stage 3: Illustrate — per-scene Dalí-style image generation via Hermes + FAL.
# Requires: pip3 install requests Pillow

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

DEFAULT_STYLE_PREFIX = (
    "Surrealist oil painting in Salvador Dalí style, "
    "meticulous brushwork, dreamlike metaphysical atmosphere, "
    "hyperrealistic surrealism, museum-quality, "
    "vertical 9:16 aspect ratio, tall portrait composition, "
    "full body framing, subject positioned in the upper two-thirds of the frame, "
)

_URL_RE = re.compile(r'https?://[^\s"]+\.(?:png|jpe?g|webp)', re.IGNORECASE)

_HERMES_PROMPT_TEMPLATE = (
    'Use the image_gen tool EXACTLY ONCE to generate ONE image with this prompt: '
    '"{full_prompt}". '
    "Do not generate more than one image. "
    "After generation, respond with ONLY the raw URL returned by image_gen. "
    "No commentary, no markdown, no code fences, no explanation. Just the URL."
)


def _build_image_prompt(
    scene_description: str,
    style_prefix: str | None,
    color_palette: list[str] | None,
    aspect_ratio: str = "9:16",
) -> str:
    prefix = style_prefix if style_prefix is not None else DEFAULT_STYLE_PREFIX
    prompt = prefix + scene_description
    if color_palette:
        palette_str = ", ".join(color_palette)
        prompt += f". Color palette: {palette_str}"
    prompt += f" Format: {aspect_ratio} aspect ratio, vertical orientation."
    return prompt


def _call_hermes(prompt: str, timeout: int) -> str:
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


def _extract_url(raw: str) -> str | None:
    """Find FAL image URL in Hermes TUI output after the response separator.

    The TUI wraps long URLs across lines (e.g. '...filename.\n     png').
    We first try a direct search, then fall back to joining stripped lines so
    split URLs are reassembled before matching.
    """
    hermes_marker = raw.find("⚕ Hermes")
    search_start = (hermes_marker + len("⚕ Hermes")) if hermes_marker != -1 else 0
    response_section = raw[search_start:]

    # Fast path: URL fits on one line.
    m = _URL_RE.search(response_section)
    if m:
        return m.group(0)

    # Slow path: strip and concatenate all lines to reassemble TUI-wrapped URLs.
    compact = "".join(line.strip() for line in response_section.splitlines())
    m = _URL_RE.search(compact)
    if m:
        return m.group(0)

    return None


def _download_image(url: str, output_path: Path) -> bool:
    """Download URL to output_path. Returns True on success."""
    import requests  # noqa: PLC0415

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        content = resp.content
        if len(content) < 100:
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        return True
    except Exception:
        return False


def _get_image_dimensions(image_path: Path) -> tuple[int, int] | None:
    """Return (width, height) using PIL. Returns None if PIL unavailable."""
    try:
        from PIL import Image  # noqa: PLC0415
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None


def illustrate_scene(
    scene_description: str,
    output_path: Path,
    style_prefix: str | None = None,
    color_palette: list[str] | None = None,
    aspect_ratio: str = "9:16",
    max_retries: int = 3,
    timeout: int = 180,
) -> dict:
    """
    Generate a single Dalí-style image for a dream scene.

    Never raises — always returns a result dict.
    """
    import time as _time

    t0 = _time.monotonic()
    full_prompt = _build_image_prompt(scene_description, style_prefix, color_palette, aspect_ratio)
    hermes_prompt = _HERMES_PROMPT_TEMPLATE.format(full_prompt=full_prompt)

    last_error: str | None = None
    fal_url: str | None = None

    for attempt in range(1, max_retries + 1):
        try:
            raw = _call_hermes(hermes_prompt, timeout)
            url = _extract_url(raw)
            if url is None:
                last_error = f"No URL found in Hermes output (attempt {attempt})"
                time.sleep(2)
                continue

            fal_url = url
            if _download_image(url, Path(output_path)):
                dims = _get_image_dimensions(Path(output_path))
                is_portrait = dims is not None and dims[1] > dims[0]
                if dims is not None and not is_portrait:
                    print(
                        f"[scene] WARNING: image is landscape {dims[0]}x{dims[1]} "
                        f"(expected portrait) — attempt {attempt}",
                        flush=True,
                    )
                    if attempt < max_retries:
                        last_error = f"Image is landscape {dims[0]}x{dims[1]}, retrying for portrait"
                        time.sleep(2)
                        continue
                return {
                    "status": "success",
                    "scene_description": scene_description,
                    "prompt": full_prompt,
                    "fal_url": fal_url,
                    "image_path": str(output_path),
                    "image_dimensions": list(dims) if dims else None,
                    "aspect_ratio_actual": f"{dims[0]}:{dims[1]}" if dims else None,
                    "attempts": attempt,
                    "error": None,
                    "duration_sec": round(_time.monotonic() - t0, 1),
                }
            else:
                last_error = f"Image download failed or empty for URL: {url} (attempt {attempt})"
                time.sleep(2)

        except subprocess.TimeoutExpired:
            last_error = f"Hermes timed out after {timeout}s (attempt {attempt})"
            time.sleep(2)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc} (attempt {attempt})"
            time.sleep(2)

    return {
        "status": "failed",
        "scene_description": scene_description,
        "prompt": full_prompt,
        "fal_url": fal_url,
        "image_path": None,
        "image_dimensions": None,
        "aspect_ratio_actual": None,
        "attempts": max_retries,
        "error": last_error,
        "duration_sec": round(time.monotonic() - t0, 1),
    }


def illustrate_dream(
    analysis: dict,
    output_dir: Path,
    max_retries: int = 3,
) -> list[dict]:
    """
    Illustrate all scenes in an analysis JSON.
    Saves as scene_1.jpeg, scene_2.jpeg, etc.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    color_palette: list[str] | None = analysis.get("color_palette")
    scenes: list[dict] = analysis.get("scenes", [])
    results = []

    for scene in scenes:
        order = scene.get("order", len(results) + 1)
        description = scene["description"]
        image_path = output_dir / f"scene_{order}.jpeg"

        print(f"[scene {order}/{len(scenes)}] Generating image...", flush=True)
        result = illustrate_scene(
            scene_description=description,
            output_path=image_path,
            color_palette=color_palette,
            aspect_ratio="9:16",
            max_retries=max_retries,
        )
        status = result["status"]
        dur = result["duration_sec"]
        print(f"[scene {order}/{len(scenes)}] {status} in {dur}s", flush=True)
        results.append(result)

    return results


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True, help="Path to analysis JSON file from analyze.py")
    ap.add_argument("--output-dir", required=True, help="Directory to write scene images")
    args = ap.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    results = illustrate_dream(analysis, Path(args.output_dir))

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(
        f"\n=== Summary: {sum(1 for r in results if r['status'] == 'success')}/"
        f"{len(results)} scenes succeeded ==="
    )
