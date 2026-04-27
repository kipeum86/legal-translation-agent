#!/usr/bin/env python3
"""Build and query a lightweight top-K Library reference index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from private_path import PathPolicyError, private_root, resolve_private_path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERM_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "terminology-manager" / "scripts"
sys.path.insert(0, str(TERM_SCRIPTS))

from term_patterns import extract_term_hits, normalize_language  # noqa: E402
from text_match import match_term  # noqa: E402


SUPPORTED_TEXT = {".md", ".txt", ".text"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rough_tokens(text: str) -> int:
    words = len([part for part in text.split() if part])
    cjk_chars = sum(1 for char in text if "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff" or "\uac00" <= char <= "\ud7af")
    return max(1, int(words * 1.3 + cjk_chars * 1.5))


def read_reference_text(path: Path) -> str:
    if path.suffix.lower() in SUPPORTED_TEXT:
        return path.read_text(encoding="utf-8")
    return ""


def source_pair_for(target_file: Path, source_root: Path) -> Path | None:
    candidate = source_root / target_file.name
    if candidate.exists():
        return candidate
    for suffix in SUPPORTED_TEXT:
        alternative = source_root / f"{target_file.stem}{suffix}"
        if alternative.exists():
            return alternative
    return None


def first_heading(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:120]
    return ""


def extract_terms_safe(text: str, lang: str) -> list[str]:
    try:
        return sorted({hit.term for hit in extract_term_hits(text, normalize_language(lang))})
    except ValueError:
        return []


def profile_root(profile: str) -> Path:
    return private_root() / "library" / profile


def reference_roots(profile: str, source_lang: str, target_lang: str) -> tuple[Path, Path]:
    pair_root = profile_root(profile) / "references" / f"{source_lang}-{target_lang}"
    return pair_root / "source", pair_root / "target"


def index_path(profile: str) -> Path:
    return profile_root(profile) / ".index" / "references.jsonl"


def style_guide_exists(profile: str, target_lang: str) -> bool:
    return (profile_root(profile) / "style-guides" / f"style-guide-{target_lang}.md").exists()


def build_index(profile: str, source_lang: str, target_lang: str) -> list[dict[str, Any]]:
    source_root, target_root = reference_roots(profile, source_lang, target_lang)
    if not target_root.exists():
        return []
    entries = []
    for target_file in sorted(path for path in target_root.iterdir() if path.is_file()):
        target_text = read_reference_text(target_file)
        if not target_text:
            continue
        source_file = source_pair_for(target_file, source_root)
        source_text = read_reference_text(source_file) if source_file else ""
        source_terms = extract_terms_safe(source_text, source_lang) if source_text else []
        entries.append(
            OrderedDict(
                [
                    ("profile", profile),
                    ("lang_pair", f"{source_lang}-{target_lang}"),
                    ("file", str(target_file)),
                    ("source_file", str(source_file) if source_file else None),
                    ("section_id", target_file.stem),
                    ("source_heading", first_heading(source_text)),
                    ("target_heading", first_heading(target_text)),
                    ("terms", source_terms),
                    ("text_hash", f"sha256:{sha256_file(target_file)}"),
                    ("target_span", target_text[:4000]),
                    ("target_token_estimate", rough_tokens(target_text[:4000])),
                ]
            )
        )
    output_path = index_path(profile)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries), encoding="utf-8")
    return entries


def load_or_build_index(profile: str, source_lang: str, target_lang: str) -> list[dict[str, Any]]:
    path = index_path(profile)
    if not path.exists():
        return build_index(profile, source_lang, target_lang)
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    current_hashes = {
        str(path): f"sha256:{sha256_file(path)}"
        for path in reference_roots(profile, source_lang, target_lang)[1].glob("*")
        if path.is_file()
    }
    indexed_hashes = {item["file"]: item.get("text_hash") for item in entries}
    if current_hashes != indexed_hashes:
        return build_index(profile, source_lang, target_lang)
    return entries


def keyword_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9가-힣一-龥]{2,}", text.lower()))


def score_entry(entry: dict[str, Any], source_text: str, current_terms: list[str], document_type: str | None) -> dict[str, Any]:
    term_matches = []
    for term in entry.get("terms", []):
        if term in current_terms or match_term(source_text, term).present:
            term_matches.append(term)
    heading_text = f"{entry.get('source_heading', '')} {entry.get('target_heading', '')}"
    heading_overlap = len(keyword_tokens(source_text[:400]) & keyword_tokens(heading_text))
    doc_bonus = 1 if document_type and document_type.lower() in entry.get("file", "").lower() else 0
    score = len(term_matches) * 10 + heading_overlap + doc_bonus
    return {
        "score": score,
        "matched_terms": term_matches,
        "document_type_bonus": bool(doc_bonus),
    }


def retrieve(args: argparse.Namespace) -> dict[str, Any]:
    source_lang = normalize_language(args.source_lang)
    target_lang = normalize_language(args.target)
    source_path = resolve_private_path(args.source)
    source_text = source_path.read_text(encoding="utf-8")
    source_terms = extract_terms_safe(source_text, source_lang)
    entries = load_or_build_index(args.profile, source_lang, target_lang)
    has_style = style_guide_exists(args.profile, target_lang)
    if not entries:
        return OrderedDict(
            [
                ("status", "STYLE_ONLY" if has_style else "SKIPPED"),
                ("skip_reason", None if has_style else f"No Library reference available for {source_lang}->{target_lang}."),
                ("profile", args.profile),
                ("lang_pair", f"{source_lang}-{target_lang}"),
                ("selected_count", 0),
                ("selected_references", []),
                ("style_guide_available", has_style),
            ]
        )

    scored = []
    for entry in entries:
        score = score_entry(entry, source_text, source_terms, args.document_type)
        item = OrderedDict(entry)
        item["score"] = score["score"]
        item["matched_terms"] = score["matched_terms"]
        item["document_type_bonus"] = score["document_type_bonus"]
        scored.append(item)
    selected = sorted(scored, key=lambda item: (-item["score"], item["file"]))[: args.top_k]
    return OrderedDict(
        [
            ("status", "PASS"),
            ("skip_reason", None),
            ("profile", args.profile),
            ("lang_pair", f"{source_lang}-{target_lang}"),
            ("top_k", args.top_k),
            ("source_terms", source_terms),
            ("selected_count", len(selected)),
            ("selected_references", selected),
            ("style_guide_available", has_style),
        ]
    )


def write_report(output: str, report: dict[str, Any]) -> Path:
    output_path = resolve_private_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select top-K Library references for a source document.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-lang", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--document-type", default=None)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = retrieve(args)
        output_path = write_report(args.output, report)
    except (OSError, json.JSONDecodeError, PathPolicyError, ValueError) as exc:
        print(f"library-retrieval: {exc}", file=sys.stderr)
        return 1
    print(f"Library retrieval: {report['status']} selected={report['selected_count']} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
