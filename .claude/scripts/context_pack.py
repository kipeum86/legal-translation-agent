#!/usr/bin/env python3
"""Build compact role-specific context packs for translation jobs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from private_path import PathPolicyError, private_root, resolve_private_path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERM_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "terminology-manager" / "scripts"
TRANSLATOR_REFS = REPO_ROOT / ".claude" / "agents" / "translator" / "references"
sys.path.insert(0, str(TERM_SCRIPTS))

from text_match import match_term  # noqa: E402


def rough_tokens(text: str) -> int:
    ascii_words = len([part for part in text.split() if part])
    cjk_chars = sum(1 for char in text if "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff" or "\uac00" <= char <= "\ud7af")
    return max(1, int(ascii_words * 1.3 + cjk_chars * 1.5))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text_if_exists(path: Path | None) -> str:
    if path and path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def working_root() -> Path:
    return private_root() / "output" / "working"


def job_root(job_id: str) -> Path:
    return working_root() / "jobs" / job_id


def first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def manifest_artifact(job_id: str, name: str) -> Path | None:
    manifest_path = job_root(job_id) / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = load_json(manifest_path)
    for item in manifest.get("artifacts", []):
        if item.get("name") == name:
            return Path(item["path"])
    return None


def resolve_source_span(job_id: str, segment: str) -> tuple[Path | None, str]:
    candidates = [
        job_root(job_id) / "segments" / segment / "source.md",
        working_root() / "segments" / segment / "source.md",
    ]
    if segment in ("all", "full", "document"):
        candidates.extend([
            manifest_artifact(job_id, "source_parsed") or Path("__missing__"),
            working_root() / "source-parsed.md",
            manifest_artifact(job_id, "source_input") or Path("__missing__"),
        ])
    path = first_existing(candidates)
    return path, read_text_if_exists(path)


def resolve_segment_artifact(job_id: str, segment: str, name: str, fallback_name: str) -> tuple[Path | None, str]:
    candidates = [
        job_root(job_id) / "segments" / segment / name,
        working_root() / "segments" / segment / name,
        manifest_artifact(job_id, fallback_name) or Path("__missing__"),
        working_root() / name,
    ]
    path = first_existing(candidates)
    return path, read_text_if_exists(path)


def load_glossary_entries(job_id: str) -> list[dict]:
    candidates = [
        manifest_artifact(job_id, "working_glossary") or Path("__missing__"),
        job_root(job_id) / "working-glossary.json",
        working_root() / "working-glossary.json",
    ]
    path = first_existing(candidates)
    if not path:
        return []
    data = load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entries", [])
    return []


def glossary_subset(entries: list[dict], source_span: str) -> list[dict]:
    subset = []
    for entry in entries:
        source_term = str(entry.get("source_term", "")).strip()
        if not source_term:
            continue
        result = match_term(source_span, source_term)
        if result.present:
            item = OrderedDict(entry)
            item["source_match_type"] = result.match_type
            subset.append(item)
    return subset


def load_structure_expectations(job_id: str, segment: str) -> dict[str, Any]:
    candidates = [
        manifest_artifact(job_id, "structural_inventory") or Path("__missing__"),
        working_root() / "structural-inventory.json",
    ]
    path = first_existing(candidates)
    if not path:
        return {"segment_id": segment}
    inventory = load_json(path)
    matching_segment = None
    for item in inventory.get("segments", []):
        if item.get("id") == segment:
            matching_segment = item
            break
    return {
        "segment_id": segment,
        "source_language": inventory.get("source_language"),
        "total_articles": inventory.get("total_articles"),
        "articles": inventory.get("articles", []),
        "segment_plan": matching_segment,
    }


def split_markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = "preamble"
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("#").strip() or "section"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if "\n".join(lines).strip()]


def select_rule_sections(text: str, *, document_type: str | None, max_chars: int = 2400) -> list[dict]:
    if not text:
        return []
    keywords = {"register", "defined", "term", "number", "article", "format", "convention"}
    if document_type:
        keywords.update(document_type.lower().replace("-", " ").split())
    selected = []
    used_chars = 0
    for heading, section in split_markdown_sections(text):
        haystack = f"{heading}\n{section}".lower()
        if selected and not any(keyword in haystack for keyword in keywords):
            continue
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        snippet = section[:remaining]
        selected.append({"heading": heading, "text": snippet})
        used_chars += len(snippet)
    return selected


def style_guide_path(profile: str | None, target: str) -> Path | None:
    if not profile:
        return None
    candidate = private_root() / "library" / profile / "style-guides" / f"style-guide-{target}.md"
    return candidate if candidate.exists() else None


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    source_path, source_span = resolve_source_span(args.job_id, args.segment)
    language_path = TRANSLATOR_REFS / f"language-guide-{args.target}.md"
    style_path = style_guide_path(args.library_profile, args.target)
    pass_a_path, pass_a = resolve_segment_artifact(args.job_id, args.segment, "pass-a.md", "pass_a")
    pass_b_path, pass_b = resolve_segment_artifact(args.job_id, args.segment, "pass-b.md", "pass_b")

    pack: OrderedDict[str, Any] = OrderedDict(
        [
            ("schema_version", 1),
            ("job_id", args.job_id),
            ("role", args.role),
            ("segment_id", args.segment),
            ("target_lang", args.target),
            ("source_path", str(source_path) if source_path else None),
            ("source_span", source_span),
            ("source_token_estimate", rough_tokens(source_span) if source_span else 0),
            ("glossary_subset", glossary_subset(load_glossary_entries(args.job_id), source_span)),
            ("structure_expectations", load_structure_expectations(args.job_id, args.segment)),
            ("language_rules_subset", select_rule_sections(read_text_if_exists(language_path), document_type=args.document_type)),
            ("style_rules_subset", select_rule_sections(read_text_if_exists(style_path), document_type=args.document_type)),
        ]
    )
    if args.role == "synthesis":
        pack["pass_a_path"] = str(pass_a_path) if pass_a_path else None
        pack["pass_a_span"] = pass_a
        pack["pass_b_path"] = str(pass_b_path) if pass_b_path else None
        pack["pass_b_span"] = pass_b
    pack["context_token_estimate"] = rough_tokens(json.dumps(pack, ensure_ascii=False))
    return pack


def write_pack(output: str, pack: dict[str, Any]) -> Path:
    output_path = resolve_private_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a compact context pack for a job segment.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--role", required=True, choices=["translator", "synthesis", "library", "reviewer"])
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--document-type", default=None)
    parser.add_argument("--library-profile", default=None)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        pack = build_pack(args)
        output_path = write_pack(args.output, pack)
    except (OSError, json.JSONDecodeError, PathPolicyError) as exc:
        print(f"build-context-pack: {exc}", file=sys.stderr)
        return 1
    print(f"Context pack: {pack['context_token_estimate']} tokens -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
