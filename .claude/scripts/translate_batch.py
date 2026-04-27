#!/usr/bin/env python3
"""Create a dry-run batch translation plan with explicit parallel phases."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from private_path import PathPolicyError, private_root, resolve_private_path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERM_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "terminology-manager" / "scripts"
sys.path.insert(0, str(TERM_SCRIPTS))

from term_patterns import extract_term_hits, normalize_language  # noqa: E402


SUPPORTED_SUFFIXES = {".docx", ".pdf", ".md", ".txt"}
TEXT_SUFFIXES = {".md", ".txt"}
DEFAULT_LLM_CONCURRENCY = 2
PARTY_NAME_PATTERNS = {
    "en": [
        (
            "en.legal_entity_suffix",
            re.compile(
                r"\b([A-Z][A-Za-z0-9&.,' -]{1,80}\b"
                r"(?:Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Co\.?|Company))\b"
            ),
        )
    ]
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def batches_root() -> Path:
    return private_root() / "output" / "working" / "batches"


def default_local_concurrency() -> int:
    return max(1, min(os.cpu_count() or 1, 4))


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def scan_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in SUPPORTED_SUFFIXES else []
    return sorted(
        path for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def per_doc_id(index: int, path: Path) -> str:
    safe_stem = "".join(char if char.isalnum() else "-" for char in path.stem).strip("-").lower()
    return f"doc-{index:03d}-{safe_stem or 'document'}"


def batch_document_root(batch_id: str, doc_id: str) -> str:
    return f"output/working/batches/{batch_id}/documents/{doc_id}"


def phase1_outputs(batch_id: str, doc_id: str) -> dict[str, str]:
    root = batch_document_root(batch_id, doc_id)
    return {
        "parsed_source": f"{root}/source-parsed.md",
        "source_structure": f"{root}/source-structure.json",
        "structural_inventory": f"{root}/structural-inventory.json",
        "term_candidates": f"{root}/term-candidates.json",
    }


def normalize_term_key(term: str) -> str:
    return " ".join(term.casefold().split())


def read_reviewable_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    return path.read_text(encoding="utf-8")


def aggregate_candidate(
    buckets: dict[str, dict[str, Any]],
    *,
    term: str,
    lock_type: str,
    doc_id: str,
    line: int,
    pattern_id: str,
    context: str,
) -> None:
    key = normalize_term_key(term)
    bucket = buckets.setdefault(
        key,
        {
            "lock_type": lock_type,
            "normalized_key": key,
            "source_terms": set(),
            "doc_ids": set(),
            "source_locations": set(),
            "pattern_ids": set(),
            "contexts": [],
            "occurrence_count": 0,
        },
    )
    bucket["source_terms"].add(term)
    bucket["doc_ids"].add(doc_id)
    bucket["source_locations"].add(f"{doc_id}:line:{line}")
    bucket["pattern_ids"].add(pattern_id)
    if context and context not in bucket["contexts"] and len(bucket["contexts"]) < 3:
        bucket["contexts"].append(context)
    bucket["occurrence_count"] += 1


def extract_party_name_hits(text: str, lang: str) -> list[dict[str, Any]]:
    hits = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern_id, pattern in PARTY_NAME_PATTERNS.get(lang, []):
            for match in pattern.finditer(line):
                hits.append(
                    {
                        "term": match.group(1).strip(),
                        "pattern_id": pattern_id,
                        "line": line_number,
                        "context": line.strip(),
                    }
                )
    return hits


def bucket_to_lock(bucket: dict[str, Any]) -> OrderedDict:
    source_terms = sorted(bucket["source_terms"])
    primary_term = source_terms[0]
    return OrderedDict(
        [
            ("lock_type", bucket["lock_type"]),
            ("source_term", primary_term),
            ("source_surface_variants", source_terms),
            ("normalized_key", bucket["normalized_key"]),
            ("doc_ids", sorted(bucket["doc_ids"])),
            ("occurrence_count", bucket["occurrence_count"]),
            ("source_locations", sorted(bucket["source_locations"])),
            ("pattern_ids", sorted(bucket["pattern_ids"])),
            ("contexts", bucket["contexts"]),
            ("status", "lock_candidate"),
            ("recommended_target_term", None),
            ("user_selected_target_term", None),
        ]
    )


def surface_variant_conflicts(locks: list[OrderedDict]) -> list[OrderedDict]:
    conflicts = []
    for lock in locks:
        if len(lock["source_surface_variants"]) > 1:
            conflicts.append(
                OrderedDict(
                    [
                        ("conflict_type", "source_surface_variant"),
                        ("lock_type", lock["lock_type"]),
                        ("normalized_key", lock["normalized_key"]),
                        ("source_terms", lock["source_surface_variants"]),
                        ("doc_ids", lock["doc_ids"]),
                        ("requires_user_decision", True),
                        ("resolution", None),
                    ]
                )
            )
    return conflicts


def collect_lock_candidates(documents: list[dict[str, Any]], source_lang: str) -> tuple[list[OrderedDict], list[OrderedDict], list[dict[str, str]]]:
    defined_terms: dict[str, dict[str, Any]] = {}
    party_names: dict[str, dict[str, Any]] = {}
    notes: list[dict[str, str]] = []
    try:
        lang = normalize_language(source_lang)
    except ValueError:
        return [], [], [{"level": "warning", "message": f"source_lang {source_lang!r} is not supported for dry-run lock extraction"}]

    for document in documents:
        path = Path(document["path"])
        text = read_reviewable_text(path)
        if text is None:
            notes.append(
                {
                    "level": "info",
                    "doc_id": document["doc_id"],
                    "message": "lock candidates will be extracted after parser output is available in Phase 1",
                }
            )
            continue
        for hit in extract_term_hits(text, lang):
            aggregate_candidate(
                defined_terms,
                term=hit.term,
                lock_type="defined_term",
                doc_id=document["doc_id"],
                line=hit.line,
                pattern_id=hit.pattern_id,
                context=hit.context,
            )
        for hit in extract_party_name_hits(text, lang):
            aggregate_candidate(
                party_names,
                term=hit["term"],
                lock_type="party_name",
                doc_id=document["doc_id"],
                line=hit["line"],
                pattern_id=hit["pattern_id"],
                context=hit["context"],
            )

    return (
        [bucket_to_lock(bucket) for bucket in sorted(defined_terms.values(), key=lambda item: item["normalized_key"])],
        [bucket_to_lock(bucket) for bucket in sorted(party_names.values(), key=lambda item: item["normalized_key"])],
        notes,
    )


def build_review_queue(plan: dict[str, Any]) -> OrderedDict:
    defined_terms, party_names, notes = collect_lock_candidates(plan["documents"], plan["source_lang"])
    conflicts = surface_variant_conflicts(defined_terms + party_names)
    requires_lock_approval = bool(defined_terms or party_names or conflicts)
    return OrderedDict(
        [
            ("schema_version", 1),
            ("batch_id", plan["batch_id"]),
            ("created_at", now_iso()),
            ("status", "pending_user_review" if requires_lock_approval else "ready"),
            ("requires_user_decision", bool(conflicts)),
            ("requires_lock_approval", requires_lock_approval),
            (
                "lock_policy",
                {
                    "automatic_conflict_resolution": False,
                    "locked_categories": ["defined_terms", "party_names"],
                    "phase_3_requires": "approved batch-glossary-review.json",
                },
            ),
            ("documents", [{"doc_id": item["doc_id"], "path": item["path"]} for item in plan["documents"]]),
            ("locks", {"defined_terms": defined_terms, "party_names": party_names}),
            ("conflicts", conflicts),
            ("extraction_notes", notes),
        ]
    )


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    input_path = resolve_private_path(args.input)
    documents = scan_inputs(input_path)
    job_id = args.job_id or str(uuid.uuid4())
    local_concurrency = args.local_concurrency or default_local_concurrency()
    llm_concurrency = args.llm_concurrency or DEFAULT_LLM_CONCURRENCY
    document_entries = [
        OrderedDict(
            [
                ("doc_id", per_doc_id(index, path)),
                ("path", str(path)),
                ("suffix", path.suffix.lower()),
                ("status", "planned"),
                ("phase1_outputs", phase1_outputs(job_id, per_doc_id(index, path))),
                ("translation_job_id", f"{job_id}-{per_doc_id(index, path)}"),
            ]
        )
        for index, path in enumerate(documents, 1)
    ]
    phase1_tasks = []
    phase2_tasks = []
    for item in document_entries:
        phase1_tasks.extend(
            [
                {
                    "doc_id": item["doc_id"],
                    "step": "parse",
                    "parallelizable": True,
                    "concurrency_pool": "local_scripts",
                    "max_concurrency": local_concurrency,
                    "output": item["phase1_outputs"]["parsed_source"],
                },
                {
                    "doc_id": item["doc_id"],
                    "step": "structure_count",
                    "parallelizable": True,
                    "concurrency_pool": "local_scripts",
                    "max_concurrency": local_concurrency,
                    "output": item["phase1_outputs"]["structural_inventory"],
                },
                {
                    "doc_id": item["doc_id"],
                    "step": "term_candidate_extraction",
                    "parallelizable": True,
                    "concurrency_pool": "local_scripts",
                    "max_concurrency": local_concurrency,
                    "output": item["phase1_outputs"]["term_candidates"],
                },
            ]
        )
        phase2_tasks.append(
            {
                "doc_id": item["doc_id"],
                "step": "translation_pipeline",
                "parallelizable": True,
                "concurrency_pool": "llm",
                "max_concurrency": llm_concurrency,
                "requires_approved_locks": ["defined_terms", "party_names"],
                "job_id": item["translation_job_id"],
            }
        )

    return OrderedDict(
        [
            ("schema_version", 1),
            ("batch_id", job_id),
            ("created_at", now_iso()),
            ("dry_run", args.dry_run),
            ("target_lang", args.target),
            ("source_lang", args.source_lang),
            ("mode", args.mode),
            ("library_profile", args.library_profile),
            ("input_path", str(input_path)),
            ("document_count", len(document_entries)),
            ("documents", document_entries),
            (
                "concurrency",
                {
                    "local_scripts": local_concurrency,
                    "llm": llm_concurrency,
                    "local_default": "min(os.cpu_count(), 4)",
                    "llm_default": DEFAULT_LLM_CONCURRENCY,
                },
            ),
            (
                "lock_policy",
                {
                    "automatic_conflict_resolution": False,
                    "batch_level_locks": ["defined_terms", "party_names"],
                    "phase_3_blocked_until": "batch-glossary-review.json approved",
                },
            ),
            ("review_queue_path", str(batches_root() / job_id / "batch-glossary-review.json")),
            ("phases", [
                {
                    "phase": 1,
                    "name": "parse-structure-terms",
                    "parallelizable": True,
                    "concurrency_pool": "local_scripts",
                    "tasks": phase1_tasks,
                },
                {
                    "phase": 2,
                    "name": "batch-glossary-review",
                    "parallelizable": False,
                    "lock": "batch_glossary",
                    "output": "batch-glossary-review.json",
                    "blocks_phase": 3,
                    "tasks": [
                        {
                            "step": "resolve_term_conflicts",
                            "requires_user_decision": True,
                            "automatic_resolution_allowed": False,
                        },
                        {
                            "step": "approve_batch_locks",
                            "requires_user_decision": True,
                            "lock_categories": ["defined_terms", "party_names"],
                        },
                    ],
                },
                {
                    "phase": 3,
                    "name": "document-translation",
                    "parallelizable": True,
                    "concurrency_pool": "llm",
                    "requires": ["batch-glossary-review.json approved"],
                    "tasks": phase2_tasks,
                },
            ]),
        ]
    )


def write_outputs(plan: dict[str, Any]) -> tuple[Path, Path]:
    root = batches_root() / plan["batch_id"]
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "batch-plan.json"
    review_path = root / "batch-glossary-review.json"
    review = build_review_queue(plan)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan_path, review_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan a batch translation run.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="Create a batch plan")
    start.add_argument("--input", required=True)
    start.add_argument("--target", required=True)
    start.add_argument("--source-lang", default="unknown")
    start.add_argument("--mode", default="normal", choices=["fast", "normal", "hard"])
    start.add_argument("--library-profile", default=None)
    start.add_argument("--job-id", default=None)
    start.add_argument("--dry-run", action="store_true")
    start.add_argument("--local-concurrency", type=positive_int, default=None)
    start.add_argument("--llm-concurrency", type=positive_int, default=DEFAULT_LLM_CONCURRENCY)
    start.set_defaults(func=start_command)
    return parser


def start_command(args: argparse.Namespace) -> int:
    try:
        plan = build_plan(args)
        plan_path, review_path = write_outputs(plan)
    except (OSError, PathPolicyError) as exc:
        print(f"translate-batch: {exc}", file=sys.stderr)
        return 1
    print(f"Batch plan: {plan['document_count']} document(s) -> {plan_path}")
    print(f"Glossary review queue: {review_path}")
    print(f"Concurrency: local_scripts={plan['concurrency']['local_scripts']}, llm={plan['concurrency']['llm']}")
    print("Locks: defined_terms + party_names require approval before Phase 3.")
    if args.dry_run:
        print("Dry-run: no documents translated.")
    return 0 if plan["document_count"] else 1


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
