"""
Backfill per-user memory profiles from existing dream.json files.
Run once from the project root: python3 pipeline/backfill_memory.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory import update_profile

DREAMER_TO_ID = {
    "@memosr": "991959357",
    "memosr": "991959357",
    "@memo_cc": "memo_cc_placeholder",
}

ARCH_FROM_MOOD = {
    "uncanny": "shadow", "foreboding": "shadow",
    "transcendent": "self", "luminous": "self",
    "liminal": "trickster", "absurd": "trickster",
    "ethereal": "anima", "wistful": "anima",
    "whimsical": "puer", "joyful": "puer",
}

dreams_dir = Path("gallery/public/dreams")
all_dreams = []
for d in sorted(dreams_dir.iterdir()):
    if not d.is_dir():
        continue
    dj = d / "dream.json"
    if not dj.exists():
        continue
    data = json.loads(dj.read_text(encoding="utf-8"))
    all_dreams.append(data)

all_dreams.sort(key=lambda d: d.get("date", ""))

for data in all_dreams:
    raw_dreamer = data.get("dreamer", "@anonymous")
    # Normalize: strip parenthetical notes like "(fictional dream for diversity testing)"
    base_dreamer = raw_dreamer.split("(")[0].strip()
    # Ensure @ prefix for lookup
    lookup_key = base_dreamer if base_dreamer.startswith("@") else base_dreamer
    user_id = DREAMER_TO_ID.get(lookup_key, lookup_key.lstrip("@"))
    # Normalize username to @-prefixed form
    username = base_dreamer if base_dreamer.startswith("@") else f"@{base_dreamer}"
    archetype = data.get("archetype") or ARCH_FROM_MOOD.get(
        (data.get("mood") or "").lower(), "unknown"
    )
    update_profile(
        user_id=user_id, username=username,
        dream_id=data["id"], title=data.get("title", "?"),
        archetype=archetype, mood=data.get("mood", "?"),
        symbols=data.get("symbols", []),
    )
    print(f"✓ {data['id']} ({data.get('title','?')}) → {user_id}")

print("\nDone. Check gallery/data/users/")
