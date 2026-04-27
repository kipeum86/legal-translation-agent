#!/usr/bin/env python3
"""Extract deterministic term candidates from source text."""

from __future__ import annotations

import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

from term_patterns import extract_term_hits, normalize_language


def build_candidates(source_path: Path, lang: str) -> dict:
    text = source_path.read_text(encoding="utf-8")
    lang = normalize_language(lang)
    grouped: dict[str, list] = defaultdict(list)
    for hit in extract_term_hits(text, lang):
        grouped[hit.term].append(hit)

    candidates = []
    for term in sorted(grouped):
        hits = grouped[term]
        candidates.append(
            OrderedDict(
                [
                    ("source_term", term),
                    ("candidate_type", hits[0].candidate_type),
                    ("source_locations", [f"line:{hit.line}" for hit in hits]),
                    ("pattern_ids", sorted({hit.pattern_id for hit in hits})),
                    ("contexts", [hit.context for hit in hits[:3]]),
                    ("llm_action", "review"),
                    ("status", "candidate"),
                ]
            )
        )

    return OrderedDict(
        [
            ("source_file", str(source_path)),
            ("source_lang", lang),
            ("candidate_count", len(candidates)),
            ("candidates", candidates),
        ]
    )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: extract-term-candidates.py <source.md> <source_lang> <output.json>", file=sys.stderr)
        return 2

    source_path = Path(argv[0])
    lang = argv[1]
    output_path = Path(argv[2])
    if not source_path.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        return 1

    try:
        payload = build_candidates(source_path, lang)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Term candidates: {payload['candidate_count']} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
