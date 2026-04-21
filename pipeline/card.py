#!/usr/bin/env python3
"""
pipeline/card.py — Dream card generator.
Produces a 1080×1920 PNG suitable for Instagram / social media.
"""

from __future__ import annotations

import colorsys
import json
import re
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Constants ────────────────────────────────────────────────────────────────

CARD_W, CARD_H = 1080, 1920
PAD_X = 60
FONT_PATH = Path("assets/fonts/PlayfairDisplay.ttf")

# Strip spans full card width, no gaps
STRIP_IMG_W = 360
STRIP_IMG_H = 640
STRIP_GAP = 0

# ── Color helpers ─────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def _darken_hsl(rgb: tuple[int, int, int], factor: float = 0.6) -> tuple[int, int, int]:
    """Darken a color by reducing HSL lightness — preserves saturation."""
    r, g, b = rgb
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    r2, g2, b2 = colorsys.hls_to_rgb(h, max(0.0, l * factor), s)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)


def _sort_palette(palette: list[str]) -> list[tuple[int, int, int]]:
    """Return list of RGB tuples sorted darkest-first by luminance."""
    rgbs = [_hex_to_rgb(h) for h in palette]
    rgbs.sort(key=_luminance)
    return rgbs


def _pick_colors(palette: list[str]):
    """Return (bg_top, bg_bot, text_color, accent_color, sep_color)."""
    sorted_rgbs = _sort_palette(palette)
    dark = [c for c in sorted_rgbs if _luminance(c) < 128]

    if len(dark) >= 2:
        bg_top, bg_bot = dark[0], dark[1]
    elif len(dark) == 1:
        # Darken via HSL so gradient looks real, not flat
        bg_top = dark[0]
        bg_bot = _darken_hsl(dark[0], factor=0.6)
    else:
        # All light — darken the darkest color
        bg_top = _darken_hsl(sorted_rgbs[0], factor=0.5)
        bg_bot = _darken_hsl(sorted_rgbs[0], factor=0.35)

    lightest = sorted_rgbs[-1]
    if _luminance(lightest) > 150:
        text_color = lightest
    else:
        text_color = (238, 228, 205)  # warm cream fallback

    accent_color = sorted_rgbs[max(0, len(sorted_rgbs) // 2)]
    sep_color = tuple(min(255, c + 50) for c in accent_color)

    return bg_top, bg_bot, text_color, accent_color, sep_color


def _draw_gradient(draw: ImageDraw.ImageDraw, w: int, h: int,
                   c_top: tuple, c_bot: tuple, steps: int = 150) -> None:
    r1, g1, b1 = c_top
    r2, g2, b2 = c_bot
    step_h = h / steps
    for i in range(steps):
        t = i / steps
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        y0 = int(i * step_h)
        y1 = int((i + 1) * step_h) + 1
        draw.rectangle([0, y0, w, y1], fill=(r, g, b))


# ── Hermes / translation ──────────────────────────────────────────────────────

def _call_hermes_plain(prompt: str, timeout: int = 120) -> str:
    result = subprocess.run(
        ["hermes", "chat", "-q", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Hermes exited {result.returncode}. stderr: {result.stderr.strip()}"
        )
    return result.stdout


def _extract_plain_response(raw: str) -> str:
    """Extract model response after the '⚕ Hermes' TUI separator."""
    marker = raw.find("⚕ Hermes")
    start = (marker + len("⚕ Hermes")) if marker != -1 else 0
    text = raw[start:].strip()
    lines = [l for l in text.splitlines()
             if not re.match(r"^\s*[│╰╭╮╯┤├┼─═]+\s*$", l)]
    result = "\n".join(lines).strip()
    # Strip Hermes session footer and everything after it
    for footer_marker in ("Resume this session with:", "\nSession:", "\nDuration:"):
        idx = result.find(footer_marker)
        if idx != -1:
            result = result[:idx].strip()
            break
    return result


def translate_to_english(text_tr: str) -> str:
    """Translate Turkish Jungian text to formal English via Hermes."""
    escaped = json.dumps(text_tr)[1:-1].replace("'", "\\'")
    prompt = (
        "Translate the following Turkish text to English. "
        "Use a formal, academic tone — as if writing for a depth psychology journal. "
        "Respond with ONLY the English translation, no quotes, no explanation: "
        f"'{escaped}'"
    )
    raw = _call_hermes_plain(prompt, timeout=120)
    return _extract_plain_response(raw)


def _is_turkish(text: str) -> bool:
    """Return True if text contains Turkish-specific characters."""
    return bool(re.search(r'[üşıöğçÜŞİÖĞÇ]', text))


def _translate_symbol(symbol: str) -> str:
    """Translate a single Turkish dream symbol to English via Hermes."""
    escaped = json.dumps(symbol)[1:-1]
    prompt = (
        "Translate this single Turkish dream symbol or short phrase to English. "
        "Use concise, evocative language. "
        "Respond with ONLY the English translation, no quotes, no explanation: "
        f"'{escaped}'"
    )
    raw = _call_hermes_plain(prompt, timeout=60)
    return _extract_plain_response(raw)


def translate_symbols(symbols: list[str], cache_path: Path,
                      force_retranslate: bool = False) -> list[str]:
    """Translate Turkish symbols to English, caching results in symbols_en.json."""
    cache: dict[str, str] = {}
    if cache_path.exists() and not force_retranslate:
        with open(cache_path) as f:
            cache = json.load(f)

    result = []
    changed = False
    for sym in symbols:
        if _is_turkish(sym):
            if sym not in cache:
                cache[sym] = _translate_symbol(sym)
                changed = True
            result.append(cache[sym])
        else:
            result.append(sym)

    if changed:
        with open(cache_path, "w") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return result


# ── Text helpers ──────────────────────────────────────────────────────────────

def _smart_truncate(text: str, max_chars: int) -> str:
    """Truncate at sentence boundary ≤ max_chars. Append '...' only if cut."""
    text = " ".join(text.split())  # normalize whitespace and newlines
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Prefer cutting at last sentence-ending punctuation
    m = list(re.finditer(r'[.!?]', chunk))
    if m:
        return text[:m[-1].end()].strip()
    # No sentence end — cut at last word boundary
    return chunk.rsplit(" ", 1)[0].rstrip() + "..."


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str,
                font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text_block(draw: ImageDraw.ImageDraw, text: str,
                     font: ImageFont.FreeTypeFont,
                     x: int, y: int, max_width: int,
                     fill: tuple, line_spacing: int = 8,
                     align: str = "left") -> int:
    """Draw wrapped text. Returns Y after the last line."""
    lines = _wrap_lines(draw, text, font, max_width)
    lh = font.size + line_spacing
    for line in lines:
        if align == "center":
            lw = draw.textlength(line, font=font)
            draw.text(((CARD_W - lw) // 2, y), line, font=font, fill=fill)
        else:
            draw.text((x, y), line, font=font, fill=fill)
        y += lh
    return y


def _draw_separator(draw: ImageDraw.ImageDraw, y: int,
                    color: tuple, pad: int = 64) -> None:
    draw.rectangle([pad, y, CARD_W - pad, y + 1], fill=color)


def _draw_chips(draw: ImageDraw.ImageDraw, symbols: list[str],
                font: ImageFont.FreeTypeFont, start_y: int,
                chip_bg: tuple, chip_text: tuple,
                pad_x: int = 60, h_pad: int = 20,
                v_pad: int = 12, gap: int = 12) -> int:
    """Draw rounded symbol chips. Returns Y after the last row."""
    x, y = pad_x, start_y
    row_h = font.size + v_pad * 2
    for sym in symbols:
        w = int(draw.textlength(sym, font=font)) + h_pad * 2
        if x + w > CARD_W - pad_x and x > pad_x:
            x = pad_x
            y += row_h + gap
        draw.rounded_rectangle(
            [x, y, x + w, y + row_h],
            radius=row_h // 2,
            fill=chip_bg,
        )
        draw.text((x + h_pad, y + v_pad), sym, font=font, fill=chip_text)
        x += w + gap
    return y + row_h


# ── Pipeline directory ─────────────────────────────────────────────────────────

def _find_scene_dir(dream_dir: Path) -> Path:
    """Return the dir with the best (9:16) scene images."""
    for candidate in ("pipeline_run_v2", "pipeline_run"):
        d = dream_dir / candidate
        if d.exists() and list(d.glob("scene_*.jpeg")):
            return d
    raise FileNotFoundError(f"No pipeline run dir with scenes found in {dream_dir}")


def _find_analysis_path(dream_dir: Path) -> Path:
    """Return the analysis path, preferring analysis_for_card.json over analysis.json."""
    for candidate in ("pipeline_run_v2", "pipeline_run"):
        d = dream_dir / candidate
        card_p = d / "analysis_for_card.json"
        if card_p.exists():
            return card_p
        p = d / "analysis.json"
        if p.exists():
            return p
    raise FileNotFoundError(f"analysis.json not found in any run dir under {dream_dir}")


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_card(
    dream_dir: Path,
    output_path: Path,
    force_retranslate: bool = False,
) -> dict:
    """
    Generate a 1080×1920 dream card PNG from a dream directory.

    Expects:
      dream_dir/
        dream.json
        pipeline_run/  (or pipeline_run_v2 — preferred)
          scene_1.jpeg, scene_2.jpeg, scene_3.jpeg
          analysis.json

    Caches:
      <run_dir>/jungian_reading_en.txt  — Jungian translation
      <run_dir>/symbols_en.json         — symbol chip translations

    Returns dict with status, output_path, file_size_kb, color_palette_used,
    translation_cached, render_time_sec, error.
    """
    t_start = time.time()
    out: dict = {
        "status": "failed",
        "output_path": str(output_path),
        "file_size_kb": None,
        "color_palette_used": None,
        "translation_cached": None,
        "render_time_sec": None,
        "error": None,
    }

    try:
        # ── Load ─────────────────────────────────────────────────────────────
        with open(dream_dir / "dream.json") as f:
            dream = json.load(f)

        scene_dir = _find_scene_dir(dream_dir)
        analysis_path = _find_analysis_path(dream_dir)

        with open(analysis_path) as f:
            analysis = json.load(f)

        # ── Colors ───────────────────────────────────────────────────────────
        palette_hex = (
            analysis.get("color_palette")
            or dream.get("color_palette")
            or ["#1A0F2E", "#2D5016", "#8B4513", "#D4A574"]
        )
        bg_top, bg_bot, text_color, accent_color, sep_color = _pick_colors(palette_hex)
        out["color_palette_used"] = palette_hex

        # ── Fonts ─────────────────────────────────────────────────────────────
        fp = str(FONT_PATH)
        title_font      = ImageFont.truetype(fp, 56)
        subtitle_font   = ImageFont.truetype(fp, 26)
        label_font      = ImageFont.truetype(fp, 17)
        transcript_font = ImageFont.truetype(fp, 32)
        jung_font       = ImageFont.truetype(fp, 30)
        chip_font       = ImageFont.truetype(fp, 26)
        footer_font1    = ImageFont.truetype(fp, 23)
        footer_font2    = ImageFont.truetype(fp, 17)

        # ── Jungian translation (cached) ──────────────────────────────────────
        en_cache = analysis_path.parent / "jungian_reading_en.txt"
        if en_cache.exists() and not force_retranslate:
            jung_en = en_cache.read_text().strip()
            out["translation_cached"] = True
        else:
            jung_tr = analysis.get("jungian_reading_tr", "")
            jung_en = translate_to_english(jung_tr) if jung_tr else ""
            en_cache.write_text(jung_en)
            out["translation_cached"] = False

        # ── Symbol translation (cached) ───────────────────────────────────────
        symbols_raw = analysis.get("symbols") or dream.get("symbols", [])
        symbols_cache = analysis_path.parent / "symbols_en.json"
        symbols = translate_symbols(symbols_raw, symbols_cache, force_retranslate)

        # ── Text content ──────────────────────────────────────────────────────
        title = dream.get("title") or analysis.get("title", "Untitled Dream")
        mood  = (analysis.get("mood") or dream.get("mood", "")).upper()
        dream_id = dream.get("id", "").upper().replace("_", " ")
        subtitle_text = f"{dream_id}  ·  {mood}" if mood else dream_id

        scenes = analysis.get("scenes", [])
        first_desc = scenes[0]["description"] if scenes else ""
        transcript_snippet = _smart_truncate(first_desc, 280) if first_desc else ""
        jung_snippet = _smart_truncate(jung_en, 280) if jung_en else ""

        # ── Scene images ──────────────────────────────────────────────────────
        scene_paths = sorted(scene_dir.glob("scene_*.jpeg"))[:3]
        scene_imgs = [
            Image.open(p).resize((STRIP_IMG_W, STRIP_IMG_H), Image.LANCZOS)
            for p in scene_paths
        ]

        # ── Canvas ────────────────────────────────────────────────────────────
        canvas = Image.new("RGB", (CARD_W, CARD_H), color=bg_top)
        draw = ImageDraw.Draw(canvas)
        _draw_gradient(draw, CARD_W, CARD_H, bg_top, bg_bot)

        # Top vignette
        for i in range(160):
            t = (160 - i) / 160
            d = int(t * 55)
            draw.rectangle(
                [0, i, CARD_W, i + 1],
                fill=tuple(max(0, c - d) for c in bg_top),
            )

        # ── Chip colors: proper luminance-based contrast ───────────────────────
        content_w = CARD_W - PAD_X * 2
        label_color = tuple(min(255, c + 90) for c in accent_color)
        chip_bg = accent_color
        # Dark chip → light text; light chip → dark text
        chip_text_color = (20, 20, 20) if _luminance(chip_bg) > 128 else (238, 228, 205)

        # ── Layout ────────────────────────────────────────────────────────────
        y = 60

        # Title
        y = _draw_text_block(draw, title, title_font,
                             PAD_X, y, content_w, text_color,
                             line_spacing=10) + 16

        # Subtitle (mood / archetype)
        y = _draw_text_block(draw, subtitle_text, subtitle_font,
                             PAD_X, y, content_w, label_color,
                             line_spacing=6) + 26

        # Separator
        _draw_separator(draw, y, sep_color)
        y += 26

        # Image strip — full card width, no gaps
        for i, img in enumerate(scene_imgs):
            canvas.paste(img, (i * STRIP_IMG_W, y))
        y += STRIP_IMG_H + 40

        # Separator
        _draw_separator(draw, y, sep_color)
        y += 52  # padding before Dream Journal

        # Dream Journal
        _draw_text_block(draw, "DREAM JOURNAL", label_font,
                         PAD_X, y, content_w, label_color)
        y += label_font.size + 12

        if transcript_snippet:
            y = _draw_text_block(draw, transcript_snippet, transcript_font,
                                 PAD_X, y, content_w, text_color,
                                 line_spacing=10) + 30
        else:
            y += 30

        # Separator
        _draw_separator(draw, y, sep_color)
        y += 48  # padding before Jungian Reading

        # Jungian Reading
        _draw_text_block(draw, "JUNGIAN READING", label_font,
                         PAD_X, y, content_w, label_color)
        y += label_font.size + 12

        if jung_snippet:
            y = _draw_text_block(draw, jung_snippet, jung_font,
                                 PAD_X, y, content_w, text_color,
                                 line_spacing=10) + 30
        else:
            y += 30

        # Separator
        _draw_separator(draw, y, sep_color)
        y += 45  # padding before chips

        # Symbol chips
        if symbols:
            _draw_chips(draw, symbols, chip_font, y,
                        chip_bg=chip_bg,
                        chip_text=chip_text_color)

        # ── Footer — fixed to bottom ──────────────────────────────────────────
        footer_y = CARD_H - 100
        footer_text1 = "ONEIRIC"
        fw1 = int(draw.textlength(footer_text1, font=footer_font1))
        draw.text(((CARD_W - fw1) // 2, footer_y), footer_text1,
                  font=footer_font1, fill=sep_color)

        footer_text2 = "dream \u2192 film  \u00b7  built on Hermes Agent"
        fw2 = int(draw.textlength(footer_text2, font=footer_font2))
        footer_color2 = tuple(max(0, c - 40) for c in sep_color)
        draw.text(((CARD_W - fw2) // 2, footer_y + 32), footer_text2,
                  font=footer_font2, fill=footer_color2)

        # ── Save ──────────────────────────────────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(output_path), format="PNG", optimize=True)

        out.update({
            "status": "success",
            "file_size_kb": round(output_path.stat().st_size / 1024, 1),
            "render_time_sec": round(time.time() - t_start, 2),
        })

    except Exception as e:
        out["error"] = str(e)

    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Generate a 1080×1920 dream card PNG")
    ap.add_argument("--dream-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--force-retranslate", action="store_true",
                    help="Ignore cached translations (Jungian + symbols)")
    args = ap.parse_args()

    result = generate_card(
        Path(args.dream_dir),
        Path(args.output),
        args.force_retranslate,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
