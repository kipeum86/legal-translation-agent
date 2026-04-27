#!/usr/bin/env python3
"""
glossary-merger.py — Merge working glossary into persistent glossary.

Implements the glossary accumulation mechanism:
- New terms: append to persistent glossary
- Existing terms: update last_used and increment usage_count
- Conflicts: log to conflicts.log, keep existing persistent version
- Library-origin terms: skip (session-scoped only, never persisted)

Usage:
    python3 glossary-merger.py <working_glossary.json> <persistent_glossary_dir> [--date YYYY-MM-DD]

The persistent glossary file is determined by the language pair in the working glossary.
File naming: glossary_{src}_{tgt}.json (alphabetically sorted pair).

Output:
- Updated persistent glossary file
- Merge report to stdout
- Conflicts appended to conflicts.log
"""

import json
import sys
from datetime import date
from pathlib import Path
from collections import OrderedDict

SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from private_path import PathPolicyError, resolve_private_path  # noqa: E402


def sort_lang_pair(src: str, tgt: str) -> tuple[str, str]:
    """Sort language pair alphabetically for consistent file naming."""
    return tuple(sorted([src.lower(), tgt.lower()]))


def glossary_filename(src: str, tgt: str) -> str:
    """Generate glossary filename from language pair."""
    a, b = sort_lang_pair(src, tgt)
    return f"glossary_{a}_{b}.json"


def load_json(path: Path) -> list[dict]:
    """Load a JSON file, returning empty list if not found or empty."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    data = json.loads(content)
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    if isinstance(data, list):
        return data
    return []


def build_term_key(entry: dict) -> str:
    """Create a unique key for a glossary entry."""
    src = entry.get("source_term", "").strip().lower()
    tgt_lang = entry.get("target_lang", "").strip().lower()
    return f"{src}|{tgt_lang}"


def merge_glossaries(
    working: list[dict],
    persistent: list[dict],
    merge_date: str,
) -> tuple[list[dict], list[dict], dict]:
    """
    Merge working glossary into persistent glossary.

    Returns: (merged_entries, conflicts, stats)
    """
    # Build lookup from persistent entries
    persistent_map = {}
    for entry in persistent:
        key = build_term_key(entry)
        persistent_map[key] = entry

    conflicts = []
    stats = {
        "working_total": len(working),
        "persistent_before": len(persistent),
        "new_added": 0,
        "updated": 0,
        "conflicts": 0,
        "skipped_library": 0,
    }

    for w_entry in working:
        # Skip library-origin entries (session-scoped only)
        if w_entry.get("origin") == "library":
            stats["skipped_library"] += 1
            continue

        key = build_term_key(w_entry)

        if key in persistent_map:
            p_entry = persistent_map[key]

            # Check for conflict: same source term, different target term
            if p_entry.get("target_term", "").strip() != w_entry.get("target_term", "").strip():
                conflicts.append({
                    "source_term": w_entry.get("source_term"),
                    "source_lang": w_entry.get("source_lang"),
                    "target_lang": w_entry.get("target_lang"),
                    "persistent_target": p_entry.get("target_term"),
                    "working_target": w_entry.get("target_term"),
                    "date": merge_date,
                    "resolution": "kept_persistent",
                })
                stats["conflicts"] += 1
                # Keep persistent version, but still update usage
                p_entry["last_used"] = merge_date
                p_entry["usage_count"] = p_entry.get("usage_count", 0) + 1
            else:
                # Same mapping — update metadata
                p_entry["last_used"] = merge_date
                p_entry["usage_count"] = p_entry.get("usage_count", 0) + 1
                # Optionally update context if working entry has richer context
                if w_entry.get("context") and not p_entry.get("context"):
                    p_entry["context"] = w_entry["context"]
                stats["updated"] += 1
        else:
            # New term — add to persistent
            new_entry = OrderedDict([
                ("source_term", w_entry.get("source_term", "")),
                ("target_term", w_entry.get("target_term", "")),
                ("source_lang", w_entry.get("source_lang", "")),
                ("target_lang", w_entry.get("target_lang", "")),
                ("context", w_entry.get("context", "")),
                ("origin", "persistent"),
                ("alternatives_considered", w_entry.get("alternatives_considered", [])),
                ("selection_rationale", w_entry.get("selection_rationale", "")),
                ("status", "confirmed"),
                ("last_used", merge_date),
                ("usage_count", 1),
            ])
            persistent_map[key] = new_entry
            stats["new_added"] += 1

    merged = list(persistent_map.values())
    stats["persistent_after"] = len(merged)
    return merged, conflicts, stats


def append_conflicts_log(conflicts: list[dict], log_path: Path):
    """Append conflicts to the conflicts.log file."""
    if not conflicts:
        return
    with open(log_path, "a", encoding="utf-8") as f:
        for c in conflicts:
            f.write(
                f"[{c['date']}] CONFLICT: '{c['source_term']}' "
                f"({c['source_lang']}→{c['target_lang']}): "
                f"persistent='{c['persistent_target']}' vs working='{c['working_target']}' "
                f"→ {c['resolution']}\n"
            )


def write_conflicts_queue(conflicts: list[dict], queue_path: Path):
    """Write machine-readable conflicts for user review."""
    if not conflicts:
        return
    existing = {"conflicts": []}
    if queue_path.exists():
        try:
            existing = json.loads(queue_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            existing = {"conflicts": []}

    queue_entries = existing.get("conflicts", [])
    for conflict in conflicts:
        queue_entries.append({
            "source_term": conflict.get("source_term", ""),
            "source_lang": conflict.get("source_lang", ""),
            "target_lang": conflict.get("target_lang", ""),
            "candidates": [
                conflict.get("persistent_target", ""),
                conflict.get("working_target", ""),
            ],
            "origins": ["persistent", "working"],
            "recommended": conflict.get("persistent_target", ""),
            "requires_user_decision": True,
            "date": conflict.get("date", ""),
        })

    queue_path.write_text(
        json.dumps({"conflicts": queue_entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_stats_file(stats: dict, stats_path: Path, merge_date: str):
    """Update the aggregate glossary statistics file."""
    existing = {}
    if stats_path.exists():
        try:
            existing = json.loads(stats_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            existing = {}

    existing["last_merge"] = merge_date
    existing["total_merges"] = existing.get("total_merges", 0) + 1
    existing["total_terms"] = stats["persistent_after"]
    existing["total_conflicts"] = existing.get("total_conflicts", 0) + stats["conflicts"]

    # Track per-merge history (keep last 50)
    history = existing.get("merge_history", [])
    history.append({
        "date": merge_date,
        "new_added": stats["new_added"],
        "updated": stats["updated"],
        "conflicts": stats["conflicts"],
    })
    existing["merge_history"] = history[-50:]

    stats_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 glossary-merger.py <working_glossary.json> <persistent_glossary_dir> [--date YYYY-MM-DD]")
        sys.exit(1)

    try:
        working_path = Path(resolve_private_path(sys.argv[1]))
        glossary_dir = Path(resolve_private_path(sys.argv[2]))
    except PathPolicyError as e:
        print(f"Error: {e}")
        sys.exit(2)

    # Optional date override
    merge_date = date.today().isoformat()
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            merge_date = sys.argv[idx + 1]

    if not working_path.exists():
        print(f"Error: Working glossary not found: {working_path}")
        sys.exit(1)

    glossary_dir.mkdir(parents=True, exist_ok=True)

    # Load working glossary
    working = load_json(working_path)
    if not working:
        print("Working glossary is empty. Nothing to merge.")
        sys.exit(0)

    # Determine language pair from first non-library entry
    src_lang = None
    tgt_lang = None
    for entry in working:
        if entry.get("origin") != "library":
            src_lang = entry.get("source_lang", "")
            tgt_lang = entry.get("target_lang", "")
            break

    if not src_lang or not tgt_lang:
        # All entries are library-origin
        print("All working glossary entries are library-origin. Nothing to persist.")
        sys.exit(0)

    # Load persistent glossary
    persistent_file = glossary_dir / glossary_filename(src_lang, tgt_lang)
    persistent = load_json(persistent_file)

    # Merge
    merged, conflicts, stats = merge_glossaries(working, persistent, merge_date)

    # Save merged persistent glossary
    output = {
        "language_pair": f"{src_lang}_{tgt_lang}",
        "last_updated": merge_date,
        "entry_count": len(merged),
        "entries": merged,
    }
    persistent_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Append conflicts
    if conflicts:
        append_conflicts_log(conflicts, glossary_dir / "conflicts.log")
        write_conflicts_queue(conflicts, working_path.parent / "glossary-conflicts-queue.json")

    # Update stats
    update_stats_file(stats, glossary_dir / "glossary-stats.json", merge_date)

    # Print report
    print(f"Glossary merge complete: {src_lang} → {tgt_lang}")
    print(f"  Working entries: {stats['working_total']}")
    print(f"  Skipped (library): {stats['skipped_library']}")
    print(f"  New terms added: {stats['new_added']}")
    print(f"  Existing updated: {stats['updated']}")
    print(f"  Conflicts (kept persistent): {stats['conflicts']}")
    print(f"  Persistent total: {stats['persistent_after']}")
    print(f"  Output: {persistent_file}")


if __name__ == "__main__":
    main()
