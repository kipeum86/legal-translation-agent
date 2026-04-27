#!/usr/bin/env python3
"""Check whether locked glossary terms are used in the translation."""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

from text_match import match_term


def load_entries(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("entries", [])
    if isinstance(data, list):
        return data
    return []


def check_usage(source_text: str, translation_text: str, entries: list[dict]) -> dict:
    findings = []
    for entry in entries:
        source_term = entry.get("source_term", "").strip()
        target_term = entry.get("target_term", "").strip()
        if not source_term or not target_term:
            continue

        source_match = match_term(source_text, source_term)
        target_match = match_term(translation_text, target_term)
        if not source_match.present:
            status = "NOT_IN_SOURCE"
            target_status = "NOT_CHECKED"
        elif target_match.match_type == "EXACT":
            status = "PASS"
            target_status = "EXACT"
        elif target_match.match_type == "NORMALIZED":
            status = "WARN"
            target_status = "NORMALIZED_ONLY"
        else:
            status = "FAIL"
            target_status = "MISSING"

        findings.append(
            OrderedDict(
                [
                    ("source_term", source_term),
                    ("target_term", target_term),
                    ("origin", entry.get("origin", "")),
                    ("status", status),
                    ("source_present", source_match.present),
                    ("source_match_type", source_match.match_type),
                    ("target_status", target_status),
                ]
            )
        )

    fail_count = sum(1 for item in findings if item["status"] == "FAIL")
    warn_count = sum(1 for item in findings if item["status"] == "WARN")
    return OrderedDict(
        [
            ("overall_status", "FAIL" if fail_count else "PASS"),
            ("checked_terms", len(findings)),
            ("fail_count", fail_count),
            ("warn_count", warn_count),
            ("findings", findings),
        ]
    )


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(
            "Usage: check-glossary-usage.py <source.md> <translation.md> <working-glossary.json> <output.json>",
            file=sys.stderr,
        )
        return 2

    source_path = Path(argv[0])
    translation_path = Path(argv[1])
    glossary_path = Path(argv[2])
    output_path = Path(argv[3])

    for path in (source_path, translation_path, glossary_path):
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            return 1

    payload = check_usage(
        source_path.read_text(encoding="utf-8"),
        translation_path.read_text(encoding="utf-8"),
        load_entries(glossary_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Glossary usage: {payload['overall_status']} -> {output_path}")
    return 0 if payload["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
