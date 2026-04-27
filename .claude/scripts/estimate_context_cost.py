#!/usr/bin/env python3
"""Estimate before/after context payload cost for prompt slimming work."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

from private_path import resolve_private_path


def rough_tokens(text: str) -> int:
    words = len([part for part in text.split() if part])
    cjk_chars = sum(1 for char in text if "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff" or "\uac00" <= char <= "\ud7af")
    return max(1, int(words * 1.3 + cjk_chars * 1.5))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_input(path_text: str) -> Path:
    return resolve_private_path(path_text)


def file_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return OrderedDict(
        [
            ("path", str(path)),
            ("byte_size", path.stat().st_size),
            ("estimated_tokens", rough_tokens(text)),
            ("fingerprint", sha256_text(text)),
        ]
    )


def build_report(before: list[Path], after: list[Path], label: str | None = None) -> dict[str, Any]:
    before_records = [file_record(path) for path in before]
    after_records = [file_record(path) for path in after]
    before_tokens = sum(item["estimated_tokens"] for item in before_records)
    after_tokens = sum(item["estimated_tokens"] for item in after_records)
    repeated = Counter(item["fingerprint"] for item in before_records)
    repeated_tokens = sum(
        item["estimated_tokens"]
        for item in before_records
        if repeated[item["fingerprint"]] > 1
    )
    saved = before_tokens - after_tokens
    reduction_ratio = saved / before_tokens if before_tokens else 0.0
    return OrderedDict(
        [
            ("label", label),
            ("before", before_records),
            ("after", after_records),
            ("total_before_tokens", before_tokens),
            ("total_after_tokens", after_tokens),
            ("estimated_saved_tokens", saved),
            ("reduction_ratio", round(reduction_ratio, 4)),
            ("repeated_source_tokens", repeated_tokens),
            ("largest_waste", "repeated identical payloads" if repeated_tokens else "none detected"),
        ]
    )


def write_report(path_text: str, report: dict[str, Any]) -> Path:
    output_path = resolve_input(path_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate context token cost before and after packing.")
    parser.add_argument("--before", nargs="+", required=True, help="Original context files")
    parser.add_argument("--after", nargs="+", required=True, help="Packed context files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", default=None)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        before = [resolve_input(item) for item in args.before]
        after = [resolve_input(item) for item in args.after]
        missing = [str(path) for path in [*before, *after] if not path.exists()]
        if missing:
            print(f"estimate-context-cost: missing file(s): {', '.join(missing)}", file=sys.stderr)
            return 1
        report = build_report(before, after, args.label)
        output_path = write_report(args.output, report)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"estimate-context-cost: {exc}", file=sys.stderr)
        return 1
    print(
        "Context cost: "
        f"{report['total_before_tokens']} -> {report['total_after_tokens']} "
        f"({report['estimated_saved_tokens']} saved) -> {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
