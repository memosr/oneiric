"""
Per-user persistent memory for Oneiric.
Hermes-native: stores markdown profiles in gallery/data/users/.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import re

MEMORY_DIR = Path("gallery/data/users")


def _profile_path(user_id: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{user_id}.md"


def load_profile(user_id: str) -> dict:
    """
    Load a user's profile and dream history.
    Returns dict with keys: exists, username, total, dreams[],
    recurring_symbols, dominant_archetypes, dominant_moods.
    """
    path = _profile_path(user_id)
    if not path.exists():
        return {
            "exists": False, "username": None, "total": 0,
            "dreams": [], "recurring_symbols": [],
            "dominant_archetypes": [], "dominant_moods": [],
        }

    text = path.read_text(encoding="utf-8")

    username_match = re.search(r"# Dreamer (@\S+)", text)
    username = username_match.group(1) if username_match else None

    dreams = []
    for line in text.split("\n"):
        m = re.match(
            r"- (dream_\d+) — \"([^\"]+)\" — (\S+)/(\S+) — (.+)",
            line.strip()
        )
        if m:
            dreams.append({
                "id": m.group(1), "title": m.group(2),
                "archetype": m.group(3), "mood": m.group(4),
                "symbols": [s.strip() for s in m.group(5).split(",")],
            })

    all_symbols: Counter = Counter()
    archetypes: Counter = Counter()
    moods: Counter = Counter()
    for d in dreams:
        all_symbols.update(d["symbols"])
        archetypes[d["archetype"]] += 1
        moods[d["mood"]] += 1

    return {
        "exists": True, "username": username, "total": len(dreams),
        "dreams": dreams,
        "recurring_symbols": [s for s, c in all_symbols.most_common(10) if c >= 2],
        "dominant_archetypes": [a for a, c in archetypes.most_common(3)],
        "dominant_moods": [m for m, c in moods.most_common(3)],
    }


def update_profile(
    user_id: str, username: str, dream_id: str, title: str,
    archetype: str, mood: str, symbols: list,
) -> None:
    """Append a new dream to the user's profile and rewrite the markdown."""
    profile = load_profile(user_id)

    new_dream = {
        "id": dream_id, "title": title,
        "archetype": archetype or "?", "mood": mood or "?",
        "symbols": symbols or [],
    }
    profile["dreams"].insert(0, new_dream)

    all_symbols: Counter = Counter()
    archetypes: Counter = Counter()
    moods: Counter = Counter()
    for d in profile["dreams"]:
        all_symbols.update(d["symbols"])
        archetypes[d["archetype"]] += 1
        moods[d["mood"]] += 1

    first_date = "today"
    if not profile["exists"]:
        first_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    md = [f"# Dreamer {username} (Telegram {user_id})\n"]
    md.append("## Profile")
    md.append(f"- First dream: {first_date}")
    md.append(f"- Total dreams: {len(profile['dreams'])}")

    recurring = [f"{s} ({c}x)" for s, c in all_symbols.most_common(10) if c >= 2]
    if recurring:
        md.append(f"- Recurring symbols: {', '.join(recurring)}")

    arch_list = [f"{a} ({c}x)" for a, c in archetypes.most_common(5) if a != "?"]
    if arch_list:
        md.append(f"- Archetype distribution: {', '.join(arch_list)}")

    mood_list = [f"{m} ({c}x)" for m, c in moods.most_common(5) if m != "?"]
    if mood_list:
        md.append(f"- Mood distribution: {', '.join(mood_list)}")

    md.append("\n## Dream history (newest first)")
    for d in profile["dreams"]:
        symbols_str = ", ".join(d["symbols"]) if d["symbols"] else "—"
        md.append(
            f"- {d['id']} — \"{d['title']}\" — "
            f"{d['archetype']}/{d['mood']} — {symbols_str}"
        )

    _profile_path(user_id).write_text("\n".join(md) + "\n", encoding="utf-8")


def context_for_kimi(user_id: str) -> str:
    """
    Build a context string to inject into Kimi's analyze prompt.
    Returns empty string if user has no history.
    """
    profile = load_profile(user_id)
    if not profile["exists"] or profile["total"] == 0:
        return ""

    lines = [
        "\n## Dreamer's previous patterns",
        f"This dreamer has shared {profile['total']} previous dream(s)."
    ]
    if profile["recurring_symbols"]:
        lines.append(
            f"Recurring symbols across their dreams: "
            f"{', '.join(profile['recurring_symbols'])}."
        )
    if profile["dominant_archetypes"]:
        lines.append(
            f"Dominant archetypes: "
            f"{', '.join(profile['dominant_archetypes'])}."
        )

    lines.append("\nMost recent dreams (newest first):")
    for d in profile["dreams"][:3]:
        symbols_str = ", ".join(d["symbols"][:5]) if d["symbols"] else "—"
        lines.append(
            f"- {d['title']} ({d['archetype']}/{d['mood']}): {symbols_str}"
        )

    lines.append(
        "\nIn your Jungian reading, if meaningful patterns emerge with the "
        "current dream — recurring symbols, archetype continuity, evolving "
        "themes — reference them naturally as a Jungian analyst would. "
        "Do NOT force connections. Only mention if genuinely relevant. "
        "Write in Turkish (jungian_reading_tr field) as before."
    )

    return "\n".join(lines)
