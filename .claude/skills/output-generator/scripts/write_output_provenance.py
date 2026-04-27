#!/usr/bin/env python3
"""Write final-output provenance and optionally check manifest freshness."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

from private_path import PathPolicyError, private_root, resolve_private_path  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, role: str, schema: str | None = None) -> dict[str, Any]:
    return OrderedDict(
        [
            ("role", role),
            ("path", str(path)),
            ("sha256", sha256_file(path)),
            ("byte_size", path.stat().st_size),
            ("schema", schema),
        ]
    )


def job_manifest(job_id: str | None) -> tuple[Path | None, dict[str, Any] | None]:
    if not job_id:
        return None, None
    path = private_root() / "output" / "working" / "jobs" / job_id / "manifest.json"
    if not path.exists():
        return path, None
    return path, json.loads(path.read_text(encoding="utf-8"))


def manifest_artifact_matches(manifest: dict[str, Any] | None, path: Path) -> bool | None:
    if manifest is None:
        return None
    resolved = str(path.resolve())
    current_hash = sha256_file(path)
    return any(
        str(Path(item.get("path", "")).resolve()) == resolved and item.get("sha256") == current_hash
        for item in manifest.get("artifacts", [])
    )


def optional_artifacts(args: argparse.Namespace) -> list[dict[str, Any]]:
    items = []
    for role, raw_path, schema in [
        ("working_glossary", args.glossary, ".claude/schemas/working-glossary.schema.json"),
        ("verification_checklist", args.checklist, ".claude/schemas/verification-checklist.schema.json"),
        ("glossary_usage_report", args.glossary_usage, ".claude/schemas/glossary-usage-report.schema.json"),
    ]:
        if raw_path:
            path = resolve_private_path(raw_path)
            if path.exists():
                items.append(artifact(path, role, schema))
    return items


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    translation = resolve_private_path(args.translation)
    output = resolve_private_path(args.output)
    manifest_path, manifest = job_manifest(args.job_id)
    input_items = [artifact(translation, "translation_body")]
    input_items.extend(optional_artifacts(args))
    return OrderedDict(
        [
            ("schema_version", 1),
            ("created_at", now_iso()),
            ("job_id", args.job_id),
            ("mode", args.mode),
            ("format", args.format),
            ("output", artifact(output, "final_output")),
            ("inputs", input_items),
            ("appendix_policy", {
                "translation_body_only_contains_translation": True,
                "security_findings_inline": False,
                "appendices": [
                    item["role"]
                    for item in input_items
                    if item["role"] != "translation_body"
                ],
            }),
            ("manifest", {
                "path": str(manifest_path) if manifest_path else None,
                "available": manifest is not None,
                "translation_source_current": manifest_artifact_matches(manifest, translation),
                "final_output_recorded": manifest_artifact_matches(manifest, output),
            }),
        ]
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write final output provenance sidecar.")
    parser.add_argument("--translation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--format", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--glossary", default=None)
    parser.add_argument("--checklist", default=None)
    parser.add_argument("--glossary-usage", default=None)
    args = parser.parse_args(argv)

    try:
        payload = build_payload(args)
        provenance_path = resolve_private_path(args.provenance)
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError, PathPolicyError) as exc:
        print(f"write-output-provenance: {exc}", file=sys.stderr)
        return 1
    print(f"Output provenance: {provenance_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
