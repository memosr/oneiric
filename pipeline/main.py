"""
Oneiric main orchestrator.
Given a dream transcript, produces a full archived dream with card.
"""
from pathlib import Path
import argparse, json, sys, time
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from analyze import analyze_dream
from illustrate import illustrate_dream
from card import generate_card


def _archetype_from_mood(mood: str) -> str:
    return {
        "uncanny": "shadow", "foreboding": "shadow",
        "transcendent": "self", "luminous": "self",
        "liminal": "trickster", "absurd": "trickster",
        "ethereal": "anima", "wistful": "anima",
        "whimsical": "puer", "joyful": "puer",
    }.get((mood or "").lower(), "unknown")


def run_pipeline(
    transcript: str,
    dream_dir: Path,
    dream_id: str,
    dreamer: str = "anonymous",
    user_id: str | None = None,
) -> dict:
    """
    Run the full dream → card pipeline.

    Returns:
        {
          "status": "success" | "partial" | "failed",
          "dream_id": str,
          "dream_dir": str,
          "card_path": str | None,
          "duration_sec": float,
          "stages": {
            "analyze": {"status", "scene_count", "title"},
            "illustrate": {"status", "success_count", "total"},
            "card": {...},
          },
          "error": str | None,
        }
    """
    start = time.time()
    dream_dir = Path(dream_dir)
    pipeline_run = dream_dir / "pipeline_run"
    pipeline_run.mkdir(parents=True, exist_ok=True)

    result = {
        "status": "pending",
        "dream_id": dream_id,
        "dream_dir": str(dream_dir),
        "card_path": None,
        "duration_sec": 0,
        "stages": {},
        "error": None,
    }

    try:
        # Save transcript
        (pipeline_run / "transcript.txt").write_text(transcript, encoding="utf-8")

        # ── Stage 1: Analyze ──────────────────────────────────────────────────
        print(f"[{dream_id}] Analyzing...", flush=True)
        analysis_path = pipeline_run / "analysis.json"
        analysis = analyze_dream(transcript, dream_id, analysis_path, user_id=user_id)
        result["stages"]["analyze"] = {
            "status": "success",
            "scene_count": len(analysis.get("scenes", [])),
            "title": analysis.get("title", "Untitled Dream"),
        }

        # card.py supports 3 scenes max — trim if needed, keep original on disk
        if len(analysis.get("scenes", [])) > 3:
            trimmed = dict(analysis)
            trimmed["scenes"] = analysis["scenes"][:3]
            card_analysis_path = pipeline_run / "analysis_for_card.json"
            card_analysis_path.write_text(
                json.dumps(trimmed, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # ── Stage 2: Illustrate ───────────────────────────────────────────────
        scene_count = len(analysis["scenes"])
        print(f"[{dream_id}] Illustrating {scene_count} scenes...", flush=True)
        illustrate_results = illustrate_dream(analysis, pipeline_run)
        success_count = sum(1 for r in illustrate_results if r["status"] == "success")
        result["stages"]["illustrate"] = {
            "status": "success" if success_count == len(illustrate_results) else "partial",
            "success_count": success_count,
            "total": len(illustrate_results),
        }

        if success_count == 0:
            result["status"] = "failed"
            result["error"] = "All scene illustrations failed."
            result["duration_sec"] = round(time.time() - start, 1)
            return result

        # ── Write dream.json BEFORE card (card.py reads it) ──────────────────
        dream_json_data = {
            "id": dream_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "dreamer": dreamer,
            "title": analysis.get("title", "Untitled Dream"),
            "transcript_tr": transcript,
            "mood": analysis.get("mood"),
            "symbols": analysis.get("symbols", []),
            "color_palette": analysis.get("color_palette", []),
            "card_path": "card.png",
            "generation_metadata": {
                "llm": "moonshotai/kimi-k2.5",
                "provider": "nous_portal",
                "orchestration": "pipeline/main.py (automated)",
                "scene_count": scene_count,
            },
        }
        (dream_dir / "dream.json").write_text(
            json.dumps(dream_json_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # ── Stage 3: Card ─────────────────────────────────────────────────────
        print(f"[{dream_id}] Generating card...", flush=True)
        card_path = dream_dir / "card.png"
        card_result = generate_card(dream_dir, card_path)
        result["stages"]["card"] = card_result

        if card_result["status"] != "success":
            result["status"] = "partial"
            result["error"] = f"Card generation failed: {card_result.get('error')}"
            result["duration_sec"] = round(time.time() - start, 1)
            return result

        result["card_path"] = str(card_path)

        # ── Update gallery/data/dreams.json ───────────────────────────────────
        dreams_json_path = Path("gallery/data/dreams.json")
        if dreams_json_path.exists():
            dreams_list = json.loads(dreams_json_path.read_text(encoding="utf-8"))
        else:
            dreams_list = []
        dreams_list = [d for d in dreams_list if d.get("id") != dream_id]
        dreams_list.append({
            "id": dream_id,
            "date": dream_json_data["date"],
            "title": dream_json_data["title"],
            "path": f"public/dreams/{dream_id}/",
            "thumbnail": "card.png",
            "mood": analysis.get("mood"),
            "dreamer": dreamer,
        })
        dreams_json_path.parent.mkdir(parents=True, exist_ok=True)
        dreams_json_path.write_text(
            json.dumps(dreams_list, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if user_id:
            from memory import update_profile
            update_profile(
                user_id=str(user_id), username=dreamer,
                dream_id=dream_id, title=analysis.get("title", "?"),
                archetype=dream_json_data.get("archetype") or
                          _archetype_from_mood(analysis.get("mood")),
                mood=analysis.get("mood"),
                symbols=analysis.get("symbols", []),
            )

        result["status"] = "success"

    except Exception as e:
        result["status"] = "failed"
        result["error"] = f"{type(e).__name__}: {e}"

    result["duration_sec"] = round(time.time() - start, 1)
    return result


def generate_dream_id() -> str:
    """Generate next sequential dream ID based on existing gallery dirs."""
    dreams_dir = Path("gallery/public/dreams")
    if not dreams_dir.exists():
        return "dream_001"
    nums = []
    for d in dreams_dir.iterdir():
        if d.is_dir() and d.name.startswith("dream_"):
            try:
                nums.append(int(d.name.split("_")[1]))
            except (IndexError, ValueError):
                pass
    next_n = (max(nums) + 1) if nums else 1
    return f"dream_{next_n:03d}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", help="Path to transcript .txt file")
    ap.add_argument("--transcript-text", help="Inline transcript text")
    ap.add_argument("--dream-id", help="Dream ID (auto-generated if omitted)")
    ap.add_argument("--dreamer", default="anonymous")
    args = ap.parse_args()

    if args.transcript:
        transcript = Path(args.transcript).read_text(encoding="utf-8").strip()
    elif args.transcript_text:
        transcript = args.transcript_text
    else:
        print("ERROR: --transcript or --transcript-text required", file=sys.stderr)
        sys.exit(1)

    dream_id = args.dream_id or generate_dream_id()
    dream_dir = Path(f"gallery/public/dreams/{dream_id}")

    result = run_pipeline(transcript, dream_dir, dream_id, args.dreamer)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] == "success" else 1)
