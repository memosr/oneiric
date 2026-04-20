#!/usr/bin/env python3
"""Stage 5: Compose — assemble dream frames + narration into a 9:16 MP4 short film."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

FFMPEG_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_BIN = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"


def _ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [FFPROBE_BIN, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _find_pipeline_dir(dream_dir: Path) -> Path:
    for name in ("pipeline_run_v2", "pipeline_run"):
        d = dream_dir / name
        if d.exists() and (d / "scene_1.jpeg").exists():
            return d
    raise FileNotFoundError(
        f"No pipeline_run_v2 or pipeline_run with scene files found in {dream_dir}"
    )


def _escape_drawtext(text: str) -> str:
    for ch, esc in [("\\", "\\\\"), ("'", "\\'"), (":", "\\:"), ("[", "\\["), ("]", "\\]")]:
        text = text.replace(ch, esc)
    return text


def compose_film(
    dream_dir: Path,
    output_path: Path,
    analysis: Optional[dict] = None,
) -> dict:
    """
    Assemble a dream into a 9:16 short film.

    Expects dream_dir structure:
      dream_dir/
        dream.json                              (has 'title', 'runs', etc.)
        pipeline_run/                           (or pipeline_run_v2)
          scene_1.jpeg
          scene_2.jpeg
          scene_3.jpeg
          transcript_narration.mp3
          jungian_narration.mp3
          analysis.json

    Smart discovery: prefer pipeline_run_v2 (9:16) over pipeline_run (16:9).
    If only pipeline_run exists, use it. If neither, raise clear error.

    Returns:
        {
          "status": "success" | "failed",
          "output_path": str,
          "duration_sec": float,
          "file_size_mb": float,
          "ffmpeg_command_preview": str (first 300 chars),
          "error": str | None,
        }
    """
    dream_dir = Path(dream_dir)
    output_path = Path(output_path)

    pipeline_dir = _find_pipeline_dir(dream_dir)

    if analysis is None:
        candidates = [
            pipeline_dir / "analysis.json",
            dream_dir / "pipeline_run" / "analysis.json",
            dream_dir / "pipeline_run_v2" / "analysis.json",
            dream_dir / "analysis.json",
        ]
        for ap in candidates:
            if ap.exists():
                with open(ap) as f:
                    analysis = json.load(f)
                break
        if analysis is None:
            raise FileNotFoundError(f"analysis.json not found near {pipeline_dir}")

    # Title: prefer dream.json top-level title, fall back to analysis
    title = analysis.get("title", "Dream")
    dream_json = dream_dir / "dream.json"
    if dream_json.exists():
        with open(dream_json) as f:
            dream_meta = json.load(f)
        title = dream_meta.get("title", title)

    # Verify required files exist
    scenes = [pipeline_dir / f"scene_{i}.jpeg" for i in range(1, 4)]
    trans_mp3 = pipeline_dir / "transcript_narration.mp3"
    jung_mp3 = pipeline_dir / "jungian_narration.mp3"
    for p in scenes + [trans_mp3, jung_mp3]:
        if not p.exists():
            raise FileNotFoundError(str(p))

    # Probe narration durations
    trans_dur = _ffprobe_duration(trans_mp3)
    jung_dur = _ffprobe_duration(jung_mp3)

    # Timing (dynamic based on narration lengths)
    title_dur = 3.0
    beat_dur = 3.0
    end_dur = 5.0
    a1s_dur = trans_dur / 3       # Act I: each of 3 scenes
    a2s_dur = jung_dur / 3        # Act II: each of 3 scenes
    fps = 30

    # Scene descriptions for subtitles
    scene_descs = [""] * 3
    for s in analysis.get("scenes", []):
        idx = s.get("order", 0) - 1
        if 0 <= idx < 3:
            scene_descs[idx] = s.get("description", "")

    # Font (absolute path)
    font_path = str(
        (Path(__file__).parent.parent / "assets" / "fonts" / "PlayfairDisplay.ttf").resolve()
    )
    if not Path(font_path).exists():
        raise FileNotFoundError(f"Font not found: {font_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write subtitle text files (textfile= is safer than inline text= for special chars)
    tmpdir = tempfile.mkdtemp(prefix="oneiric_compose_")
    sub_files = []
    for i, desc in enumerate(scene_descs):
        short = desc[:130]
        lines = textwrap.wrap(short, width=42)[:3]
        sub_file = os.path.join(tmpdir, f"sub_{i+1}.txt")
        with open(sub_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        sub_files.append(sub_file)

    W, H = 576, 1024
    size = f"{W}x{H}"
    title_esc = _escape_drawtext(title)

    # ──────────────────────────────────────────────────────────────────
    # Build filter_complex
    #
    # Input structure (command line):
    #   [0] [1] [2] → scene 1/2/3 (-framerate 1 -loop 1, shared by Act I & II)
    #   [3]         → transcript_narration.mp3
    #   [4]         → jungian_narration.mp3
    #
    # Key insight: zoompan with d=99999 runs indefinitely; trim=end=X
    # provides reliable duration control regardless of d semantics.
    # split=2 lets the same scene feed both Act I (zoom-in) and Act II
    # (zoom-out) without duplicating input files.
    # ──────────────────────────────────────────────────────────────────

    parts = []

    # Split each scene into two streams (Act I and Act II)
    for i in range(3):
        parts.append(f"[{i}:v]split=2[_s{i}a][_s{i}b]")

    # Title card: black source + centered title with fade
    parts.append(f"color=c=black:s={size}:r={fps}:d={title_dur}[_tc_bg]")
    parts.append(
        f"[_tc_bg]drawtext="
        f"fontfile='{font_path}':text='{title_esc}':"
        f"fontsize=48:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,{title_dur-0.5:.2f}),({title_dur:.2f}-t)/0.5,1))'[title_v]"
    )

    # Act I scenes: zoom in, subtitle at bottom
    for i in range(3):
        sf = sub_files[i]
        parts.append(
            f"[_s{i}a]"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,"
            f"zoompan="
            f"z='min(zoom+0.0015,1.3)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=99999:s={size}:fps={fps},"
            f"trim=end={a1s_dur:.3f},setpts=PTS-STARTPTS,"
            f"drawtext="
            f"fontfile='{font_path}':textfile='{sf}':"
            f"fontsize=28:fontcolor=0xF5E6D3:"
            f"shadowcolor=black:shadowx=2:shadowy=2:"
            f"box=1:boxcolor=0x00000088:boxborderw=12:"
            f"x=(w-text_w)/2:y=h-170:"
            f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,{a1s_dur-0.5:.3f}),({a1s_dur:.3f}-t)/0.5,1))'[a1s{i+1}]"
        )

    # Beat: 3s black between acts
    parts.append(f"color=c=black:s={size}:r={fps}:d={beat_dur}[beat_v]")

    # Act II scenes: zoom out, no subtitle
    for i in range(3):
        parts.append(
            f"[_s{i}b]"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,"
            f"zoompan="
            f"z='max(1.0,1.3-0.0015*(on-1))':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=99999:s={size}:fps={fps},"
            f"trim=end={a2s_dur:.3f},setpts=PTS-STARTPTS[a2s{i+1}]"
        )

    # End card: ONEIRIC + tagline with fade
    parts.append(f"color=c=black:s={size}:r={fps}:d={end_dur}[_ec_bg]")
    parts.append(
        f"[_ec_bg]"
        f"drawtext=fontfile='{font_path}':text='ONEIRIC':"
        f"fontsize=72:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,{end_dur-0.5:.2f}),({end_dur:.2f}-t)/0.5,1))',"
        f"drawtext=fontfile='{font_path}':text='built on Hermes Agent':"
        f"fontsize=24:fontcolor=0xBBBBBB:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+60:"
        f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,{end_dur-0.5:.2f}),({end_dur:.2f}-t)/0.5,1))'[end_v]"
    )

    # Concat all 9 video segments
    parts.append(
        "[title_v][a1s1][a1s2][a1s3][beat_v][a2s1][a2s2][a2s3][end_v]"
        "concat=n=9:v=1:a=0[vout]"
    )

    # Audio: silence + transcript + silence + jungian + silence
    parts.append(
        f"anullsrc=r=44100:cl=stereo,atrim=duration={title_dur},asetpts=PTS-STARTPTS[sil0]"
    )
    parts.append(
        f"anullsrc=r=44100:cl=stereo,atrim=duration={beat_dur},asetpts=PTS-STARTPTS[sil1]"
    )
    parts.append(
        f"anullsrc=r=44100:cl=stereo,atrim=duration={end_dur},asetpts=PTS-STARTPTS[sil2]"
    )
    parts.append(
        "[sil0][3:a][sil1][4:a][sil2]concat=n=5:v=0:a=1[aout]"
    )

    filter_complex = ";\n".join(parts)

    # Build FFmpeg command
    # Images use -framerate 1 -loop 1 (creates 1fps infinite stream,
    # zoompan + trim handles actual duration)
    cmd = [FFMPEG_BIN, "-y"]
    for scene_f in scenes:
        cmd += ["-framerate", "1", "-loop", "1", "-i", str(scene_f)]
    cmd += ["-i", str(trans_mp3), "-i", str(jung_mp3)]

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "28",
        "-maxrate", "8M", "-bufsize", "16M",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        stderr_tail = result.stderr[-3000:]
        fallback_result = _compose_fallback(
            scenes, trans_mp3, jung_mp3,
            trans_dur, title, title_dur, end_dur,
            font_path, size, fps, output_path,
        )
        if fallback_result["status"] == "success":
            fallback_result["error"] = (
                f"[Full version failed — fallback used] {stderr_tail[:600]}"
            )
            return fallback_result
        return {
            "status": "failed",
            "output_path": str(output_path),
            "duration_sec": None,
            "file_size_mb": None,
            "ffmpeg_command_preview": " ".join(cmd)[:300],
            "error": stderr_tail,
        }

    duration_sec = _ffprobe_duration(output_path)
    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    return {
        "status": "success",
        "output_path": str(output_path),
        "duration_sec": round(duration_sec, 2),
        "file_size_mb": round(file_size_mb, 2),
        "ffmpeg_command_preview": " ".join(cmd)[:300],
        "error": None,
    }


def _compose_fallback(
    scenes, trans_mp3, jung_mp3,
    trans_dur, title,
    title_dur, end_dur,
    font_path, size, fps, output_path,
) -> dict:
    """Fallback: static images (no Ken Burns), transcript only (no Jungian act)."""
    a1s_dur = trans_dur / 3
    title_esc = _escape_drawtext(title)

    parts = []
    parts.append(f"color=c=black:s={size}:r={fps}:d={title_dur}[_tc_bg]")
    parts.append(
        f"[_tc_bg]drawtext=fontfile='{font_path}':text='{title_esc}':"
        f"fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[title_v]"
    )
    for i in range(3):
        parts.append(
            f"[{i}:v]scale={size},setsar=1,fps={fps},"
            f"trim=end={a1s_dur:.3f},setpts=PTS-STARTPTS[a1s{i+1}]"
        )
    parts.append(f"color=c=black:s={size}:r={fps}:d={end_dur}[_ec_bg]")
    parts.append(
        f"[_ec_bg]drawtext=fontfile='{font_path}':text='ONEIRIC':"
        f"fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[end_v]"
    )
    parts.append("[title_v][a1s1][a1s2][a1s3][end_v]concat=n=5:v=1:a=0[vout]")
    parts.append(
        f"anullsrc=r=44100:cl=stereo,atrim=duration={title_dur},asetpts=PTS-STARTPTS[sil0]"
    )
    parts.append(
        f"anullsrc=r=44100:cl=stereo,atrim=duration={end_dur},asetpts=PTS-STARTPTS[sil1]"
    )
    parts.append("[sil0][3:a][sil1]concat=n=3:v=0:a=1[aout]")

    filter_complex = ";\n".join(parts)
    cmd = [FFMPEG_BIN, "-y"]
    for sf in scenes:
        cmd += ["-framerate", "1", "-loop", "1", "-i", str(sf)]
    cmd += ["-i", str(trans_mp3)]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "status": "failed",
            "output_path": str(output_path),
            "duration_sec": None,
            "file_size_mb": None,
            "ffmpeg_command_preview": " ".join(cmd)[:300],
            "error": result.stderr[-2000:],
        }
    duration_sec = _ffprobe_duration(output_path)
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    return {
        "status": "success",
        "output_path": str(output_path),
        "duration_sec": round(duration_sec, 2),
        "file_size_mb": round(file_size_mb, 2),
        "ffmpeg_command_preview": " ".join(cmd)[:300],
        "error": None,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Compose a dream into a 9:16 short film.")
    ap.add_argument("--dream-dir", required=True,
                    help="Path to dream directory (e.g., gallery/public/dreams/dream_001)")
    ap.add_argument("--output", required=True, help="Output .mp4 path")
    args = ap.parse_args()

    result = compose_film(Path(args.dream_dir), Path(args.output))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "success":
        sys.exit(1)
