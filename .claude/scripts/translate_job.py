#!/usr/bin/env python3
"""Minimal file-backed job orchestrator for translation workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from private_path import PathPolicyError, private_root, resolve_private_path
from validate_artifact import validate


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_SCHEMA = REPO_ROOT / ".claude" / "schemas" / "checkpoint.schema.json"
MANIFEST_SCHEMA = REPO_ROOT / ".claude" / "schemas" / "manifest.schema.json"
VALIDATION_POLICIES = {"warn", "enforce-new-jobs", "enforce-all"}

MODE_STEPS = {
    "fast": [
        {"step": 1, "name": "Document Ingestion & Analysis", "status": "pending"},
        {"step": 2, "name": "Terminology Extraction & Glossary Setup", "status": "pending"},
        {"step": 3, "name": "Single Translation Draft", "status": "pending"},
        {"step": 4, "name": "Structural & Glossary Verification", "status": "pending"},
        {"step": 5, "name": "Draft Output Assembly", "status": "pending"},
    ],
    "normal": [
        {"step": 1, "name": "Document Ingestion & Analysis", "status": "pending"},
        {"step": 2, "name": "Terminology Extraction & Glossary Setup", "status": "pending"},
        {"step": 3, "name": "Translation Pass A", "status": "pending"},
        {"step": 4, "name": "Translation Pass B", "status": "pending"},
        {"step": 5, "name": "Comparative Synthesis", "status": "pending"},
        {"step": 6, "name": "Structural Verification", "status": "pending"},
        {"step": 7, "name": "Output Assembly & Quality Gate", "status": "pending"},
    ],
    "hard": [
        {"step": 1, "name": "Document Ingestion & Analysis", "status": "pending"},
        {"step": 2, "name": "Terminology Extraction & Glossary Setup", "status": "pending"},
        {"step": 3, "name": "Translation Pass A", "status": "pending"},
        {"step": 4, "name": "Translation Pass B", "status": "pending"},
        {"step": 5, "name": "Comparative Synthesis", "status": "pending"},
        {"step": 6, "name": "Structural Verification", "status": "pending"},
        {"step": 7, "name": "Output Assembly & Quality Gate", "status": "pending"},
        {"step": 8, "name": "Back-Translation Verification", "status": "pending"},
        {"step": 9, "name": "Library Reference Comparison", "status": "pending"},
        {"step": 10, "name": "Editorial Polish & Final Quality Gate", "status": "pending"},
    ],
}

MODE_EXPECTED_ARTIFACTS = {
    "fast": [
        "source_input",
        "source_structure",
        "structural_inventory",
        "term_candidates",
        "working_glossary",
        "fast_draft",
        "target_structural_inventory",
        "verification_checklist",
        "glossary_usage_report",
        "draft_output",
        "output_provenance",
    ],
    "normal": [
        "source_input",
        "source_structure",
        "structural_inventory",
        "term_candidates",
        "working_glossary",
        "pass_a",
        "pass_b",
        "synthesized",
        "synthesis_log",
        "target_structural_inventory",
        "verification_checklist",
        "glossary_usage_report",
        "final_output",
        "output_provenance",
    ],
    "hard": [
        "source_input",
        "source_structure",
        "structural_inventory",
        "term_candidates",
        "working_glossary",
        "pass_a",
        "pass_b",
        "synthesized",
        "synthesis_log",
        "target_structural_inventory",
        "verification_checklist",
        "glossary_usage_report",
        "normal_quality_gate",
        "back_translation_report",
        "library_retrieval_report",
        "library_comparison_report",
        "editorial_change_log",
        "final_output",
        "output_provenance",
    ],
}

MODE_MODEL_CALLS = {
    "fast": [
        {
            "step": 3,
            "name": "single translation draft",
            "actor": "translator",
            "strategy": "fast-draft",
            "required": True,
            "output": "fast-draft.md",
        },
    ],
    "normal": [
        {
            "step": 3,
            "name": "translation pass A",
            "actor": "translator",
            "strategy": "source-faithful",
            "required": True,
            "output": "pass-a.md",
        },
        {
            "step": 4,
            "name": "translation pass B",
            "actor": "translator",
            "strategy": "target-drafting",
            "required": True,
            "output": "pass-b.md",
        },
        {
            "step": 5,
            "name": "comparative synthesis",
            "actor": "synthesis-editor",
            "strategy": "source-and-glossary-grounded-synthesis",
            "required": True,
            "output": "synthesized.md",
        },
    ],
    "hard": [
        {
            "step": 3,
            "name": "translation pass A",
            "actor": "translator",
            "strategy": "source-faithful",
            "required": True,
            "output": "pass-a.md",
        },
        {
            "step": 4,
            "name": "translation pass B",
            "actor": "translator",
            "strategy": "target-drafting",
            "required": True,
            "output": "pass-b.md",
        },
        {
            "step": 5,
            "name": "comparative synthesis",
            "actor": "synthesis-editor",
            "strategy": "source-and-glossary-grounded-synthesis",
            "required": True,
            "output": "synthesized.md",
        },
        {
            "step": 8,
            "name": "back-translation verification",
            "actor": "translator",
            "strategy": "back-translation",
            "required": True,
            "output": "back-translation-report.json",
        },
        {
            "step": 9,
            "name": "library reference comparison",
            "actor": "library-comparator",
            "strategy": "top-k-reference-comparison",
            "required": False,
            "condition": "Library reference or style-guide assets exist for the language pair",
            "output": "library-comparison-report.json",
        },
        {
            "step": 10,
            "name": "editorial polish",
            "actor": "editorial-reviewer",
            "strategy": "native-legal-editorial-review",
            "required": True,
            "output": "editorial-change-log.json",
        },
    ],
}

MODE_QUALITY_GATES = {
    "fast": "draft-deterministic-structure-and-glossary",
    "normal": "normal-6-item-quality-gate",
    "hard": "hard-10-item-quality-gate",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jobs_root() -> Path:
    return private_root() / "output" / "working" / "jobs"


def job_dir(job_id: str) -> Path:
    return jobs_root() / job_id


def checkpoint_path(job_id: str) -> Path:
    return job_dir(job_id) / "checkpoint.json"


def manifest_path(job_id: str) -> Path:
    return job_dir(job_id) / "manifest.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_validation_policy(raw_policy: str | None = None, manifest: dict[str, Any] | None = None) -> str:
    policy = raw_policy or os.environ.get("LEGAL_TRANSLATION_VALIDATION_POLICY") or None
    if policy is None and manifest is not None:
        policy = manifest.get("validation_policy")
    policy = policy or "warn"
    if policy not in VALIDATION_POLICIES:
        raise ValueError(f"Unsupported validation policy: {policy}. Use one of {sorted(VALIDATION_POLICIES)}")
    return policy


def validation_enforced(policy: str, manifest: dict[str, Any]) -> bool:
    if policy == "warn":
        return False
    if policy == "enforce-all":
        return True
    return manifest.get("validation_policy") in {"enforce-new-jobs", "enforce-all"}


def validate_checkpoint(payload: dict[str, Any]) -> list[str]:
    schema = load_json(CHECKPOINT_SCHEMA)
    return validate(payload, schema)


def validate_manifest(payload: dict[str, Any]) -> list[str]:
    schema = load_json(MANIFEST_SCHEMA)
    return validate(payload, schema)


def artifact_record(name: str, path: Path, step: int, schema: Path | None = None) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": name,
        "path": str(path),
        "sha256": sha256_file(path),
        "byte_size": stat.st_size,
        "created_at": now_iso(),
        "producing_step": step,
        "schema": str(schema) if schema else None,
    }


def mode_plan(mode: str) -> dict[str, Any]:
    calls = deepcopy(MODE_MODEL_CALLS[mode])
    required_calls = sum(1 for call in calls if call.get("required", True))
    conditional_calls = len(calls) - required_calls
    artifacts = list(MODE_EXPECTED_ARTIFACTS[mode])
    steps = deepcopy(MODE_STEPS[mode])
    return {
        "mode": mode,
        "draft_only": mode == "fast",
        "final_step": steps[-1]["step"],
        "quality_gate": MODE_QUALITY_GATES[mode],
        "expected_artifacts": artifacts,
        "artifact_count": len(artifacts),
        "model_call_plan": calls,
        "required_model_call_count": required_calls,
        "conditional_model_call_count": conditional_calls,
    }


def create_checkpoint(args: argparse.Namespace, job_id: str, source: Path) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "job_id": job_id,
        "started": timestamp,
        "last_updated": timestamp,
        "current_step": 1,
        "last_completed_step": 0,
        "status": "in_progress",
        "mode": args.mode,
        "source_lang": args.source_lang,
        "target_lang": args.target,
        "document_type": args.document_type,
        "library_profile": args.library_profile,
        "output_format": args.output_format,
        "retry_count": 0,
        "retry_budget": args.retry_budget,
        "failure_reason": None,
        "failure_history": [],
        "validation_policy": resolve_validation_policy(getattr(args, "validation_policy", None)),
        "validation_warnings": [],
        "artifacts": {
            "source_input": str(source),
        },
    }


def create_manifest(args: argparse.Namespace, job_id: str, source: Path, dry_run: bool) -> dict[str, Any]:
    steps = deepcopy(MODE_STEPS[args.mode])

    return {
        "schema_version": 1,
        "job_id": job_id,
        "created_at": now_iso(),
        "dry_run": dry_run,
        "retry_budget": args.retry_budget,
        "validation_policy": resolve_validation_policy(getattr(args, "validation_policy", None)),
        "input": {
            "path": str(source),
            "sha256": sha256_file(source) if source.exists() and source.is_file() else None,
            "byte_size": source.stat().st_size if source.exists() and source.is_file() else None,
        },
        "artifacts": [artifact_record("source_input", source, 0)],
        "failure_events": [],
        "validation_events": [],
        "mode_plan": mode_plan(args.mode),
        "requested": {
            "target_lang": args.target,
            "source_lang": args.source_lang,
            "mode": args.mode,
            "output_format": args.output_format,
            "library_profile": args.library_profile,
            "document_type": args.document_type,
        },
        "steps": steps,
    }


def start(args: argparse.Namespace) -> int:
    try:
        source = resolve_private_path(args.input)
    except PathPolicyError as exc:
        print(f"translate-job: {exc}", file=sys.stderr)
        return 2

    if not source.exists():
        print(f"translate-job: input file not found: {source}", file=sys.stderr)
        return 1

    job_id = args.job_id or str(uuid.uuid4())
    directory = job_dir(job_id)
    if directory.exists():
        print(f"translate-job: job already exists: {job_id}", file=sys.stderr)
        return 1

    checkpoint = create_checkpoint(args, job_id, source)
    errors = validate_checkpoint(checkpoint)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    manifest = create_manifest(args, job_id, source, args.dry_run)
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    write_json(checkpoint_path(job_id), checkpoint)
    write_json(manifest_path(job_id), manifest)
    print(f"Job created: {job_id}")
    print(f"Checkpoint: {checkpoint_path(job_id)}")
    print(f"Manifest: {manifest_path(job_id)}")
    if args.dry_run:
        print("Dry-run: no pipeline steps executed.")
    return 0


def status(args: argparse.Namespace) -> int:
    path = checkpoint_path(args.job_id)
    manifest = manifest_path(args.job_id)
    if not path.exists():
        print(f"translate-job: checkpoint not found for job {args.job_id}", file=sys.stderr)
        return 1
    if not manifest.exists():
        print(f"translate-job: manifest not found for job {args.job_id}", file=sys.stderr)
        return 1
    checkpoint = load_json(path)
    manifest_payload = load_json(manifest)
    errors = validate_checkpoint(checkpoint)
    if errors:
        print(f"Job {args.job_id}: INVALID checkpoint")
        for error in errors:
            print(f"  {error}")
        return 1
    manifest_errors = validate_manifest(manifest_payload)
    if manifest_errors:
        print(f"Job {args.job_id}: INVALID manifest")
        for error in manifest_errors:
            print(f"  {error}")
        return 1
    print(f"Job {args.job_id}: {checkpoint['status']}")
    print(f"  mode: {checkpoint['mode']}")
    print(f"  source -> target: {checkpoint['source_lang']} -> {checkpoint['target_lang']}")
    print(f"  last_completed_step: {checkpoint['last_completed_step']}")
    print(f"  current_step: {checkpoint['current_step']}")
    print(f"  retries: {checkpoint['retry_count']}/{checkpoint['retry_budget']}")
    if checkpoint.get("failure_reason"):
        print(f"  last_failure: {checkpoint['failure_reason']}")
    print(f"  validation_policy: {checkpoint.get('validation_policy', 'warn')}")
    warning_count = len(checkpoint.get("validation_warnings", []))
    if warning_count:
        print(f"  validation_warnings: {warning_count}")
    plan = manifest_payload.get("mode_plan", {})
    if plan:
        print(f"  final_step: {plan['final_step']}")
        print(
            "  model_calls: "
            f"{plan['required_model_call_count']} required"
            f" + {plan['conditional_model_call_count']} conditional"
        )
        print(f"  planned_artifacts: {plan['artifact_count']}")
    return 0


def load_validated_job(job_id: str) -> tuple[dict[str, Any], dict[str, Any]] | tuple[None, None]:
    checkpoint_file = checkpoint_path(job_id)
    manifest_file = manifest_path(job_id)
    if not checkpoint_file.exists():
        print(f"translate-job: checkpoint not found for job {job_id}", file=sys.stderr)
        return None, None
    if not manifest_file.exists():
        print(f"translate-job: manifest not found for job {job_id}", file=sys.stderr)
        return None, None

    checkpoint = load_json(checkpoint_file)
    manifest = load_json(manifest_file)
    errors = validate_checkpoint(checkpoint) + validate_manifest(manifest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return None, None
    return checkpoint, manifest


def verify_manifest_artifacts(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    issues = []
    for item in manifest.get("artifacts", []):
        artifact_path = Path(item["path"])
        if not artifact_path.exists():
            issues.append((item["name"], "missing"))
            continue
        expected_sha = item.get("sha256")
        if expected_sha and sha256_file(artifact_path) != expected_sha:
            issues.append((item["name"], "checksum_mismatch"))
    return issues


def resume(args: argparse.Namespace) -> int:
    checkpoint, manifest = load_validated_job(args.job_id)
    if checkpoint is None or manifest is None:
        return 1

    missing = []
    for name, artifact in checkpoint.get("artifacts", {}).items():
        artifact_path = Path(artifact)
        if not artifact_path.exists():
            missing.append((name, artifact))
    manifest_issues = verify_manifest_artifacts(manifest)

    print(f"Resume check for job {args.job_id}")
    print(f"  next_step: {checkpoint['current_step']}")
    if missing:
        print("  missing artifacts:")
        for name, artifact in missing:
            print(f"    {name}: {artifact}")
        return 1
    if manifest_issues:
        print("  manifest artifact issues:")
        for name, issue in manifest_issues:
            print(f"    {name}: {issue}")
        return 1
    print("  all referenced artifacts exist")
    print("  manifest checksums verified")
    if args.dry_run:
        print("Dry-run: resume did not execute pipeline steps.")
    return 0


def record_artifact(args: argparse.Namespace) -> int:
    checkpoint, manifest = load_validated_job(args.job_id)
    if checkpoint is None or manifest is None:
        return 1
    try:
        path = resolve_private_path(args.path)
        schema = Path(args.schema).resolve() if args.schema else None
    except PathPolicyError as exc:
        print(f"translate-job: {exc}", file=sys.stderr)
        return 2

    if not path.exists():
        print(f"translate-job: artifact not found: {path}", file=sys.stderr)
        return 1
    if schema:
        errors = validate(load_json(path), load_json(schema))
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1

    checkpoint["artifacts"][args.name] = str(path)
    checkpoint["last_updated"] = now_iso()
    if args.complete_step:
        checkpoint["last_completed_step"] = max(checkpoint["last_completed_step"], args.step)
        checkpoint["current_step"] = min(args.step + 1, len(manifest["steps"]))
        if checkpoint["last_completed_step"] >= len(manifest["steps"]):
            checkpoint["status"] = "completed"

    record = artifact_record(args.name, path, args.step, schema)
    manifest["artifacts"] = [item for item in manifest["artifacts"] if item["name"] != args.name]
    manifest["artifacts"].append(record)
    for item in manifest["steps"]:
        if item["step"] == args.step:
            item["status"] = "completed" if args.complete_step else "in_progress"

    errors = validate_checkpoint(checkpoint) + validate_manifest(manifest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    write_json(checkpoint_path(args.job_id), checkpoint)
    write_json(manifest_path(args.job_id), manifest)
    print(f"Artifact recorded: {args.name} -> {path}")
    return 0


def apply_failure(checkpoint: dict[str, Any], manifest: dict[str, Any], step: int, reason: str) -> None:
    event = {
        "step": step,
        "reason": reason,
        "recorded_at": now_iso(),
        "retry_count_after": checkpoint["retry_count"] + 1,
    }
    checkpoint["retry_count"] += 1
    checkpoint["failure_reason"] = reason
    checkpoint["failure_history"].append(event)
    checkpoint["last_updated"] = now_iso()
    checkpoint["status"] = "failed" if checkpoint["retry_count"] > checkpoint["retry_budget"] else "paused"
    manifest["failure_events"].append(event)
    for item in manifest["steps"]:
        if item["step"] == step:
            item["status"] = "failed" if checkpoint["status"] == "failed" else "retry_pending"


def record_failure(args: argparse.Namespace) -> int:
    checkpoint, manifest = load_validated_job(args.job_id)
    if checkpoint is None or manifest is None:
        return 1
    step = args.step or checkpoint["current_step"]
    apply_failure(checkpoint, manifest, step, args.reason)

    errors = validate_checkpoint(checkpoint) + validate_manifest(manifest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    write_json(checkpoint_path(args.job_id), checkpoint)
    write_json(manifest_path(args.job_id), manifest)
    print(f"Failure recorded for job {args.job_id}: {args.reason}")
    print(f"Retries: {checkpoint['retry_count']}/{checkpoint['retry_budget']}")
    return 0


def get_path(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted_path)
    return current


def parse_expected(raw: str) -> tuple[str, Any]:
    if "=" not in raw:
        raise ValueError(f"Expectation must be FIELD=VALUE: {raw}")
    field, value = raw.split("=", 1)
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    return field, parsed_value


def validate_expectations(data: dict[str, Any], expectations: list[str]) -> list[str]:
    errors = []
    for raw in expectations:
        field, expected = parse_expected(raw)
        try:
            actual = get_path(data, field)
        except KeyError:
            errors.append(f"{field}: missing expected field")
            continue
        if actual != expected:
            errors.append(f"{field}: expected {expected!r}, got {actual!r}")
    return errors


def validation_event(
    args: argparse.Namespace,
    artifact_path: Path,
    policy: str,
    enforced: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "step": args.step,
        "name": args.name,
        "artifact": str(artifact_path),
        "schema": str(Path(args.schema).resolve()) if args.schema else None,
        "policy": policy,
        "enforced": enforced,
        "status": "PASS" if not errors else "FAIL" if enforced else "WARN",
        "errors": errors,
        "recorded_at": now_iso(),
    }


def validate_gate(args: argparse.Namespace) -> int:
    checkpoint, manifest = load_validated_job(args.job_id)
    if checkpoint is None or manifest is None:
        return 1
    try:
        artifact_path = resolve_private_path(args.artifact)
        policy = resolve_validation_policy(args.validation_policy, manifest)
    except (PathPolicyError, ValueError) as exc:
        print(f"translate-job: {exc}", file=sys.stderr)
        return 2

    errors = []
    data: dict[str, Any] | None = None
    if not artifact_path.exists():
        errors.append(f"artifact not found: {artifact_path}")
    else:
        try:
            if args.schema or args.expect:
                data = load_json(artifact_path)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON: {exc}")

    if args.schema and data is not None:
        schema_path = Path(args.schema).resolve()
        try:
            errors.extend(validate(data, load_json(schema_path)))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"schema load failed: {exc}")
    if args.expect and data is not None:
        try:
            errors.extend(validate_expectations(data, args.expect))
        except ValueError as exc:
            errors.append(str(exc))

    enforced = bool(errors) and validation_enforced(policy, manifest)
    event = validation_event(args, artifact_path, policy, enforced, errors)
    manifest.setdefault("validation_events", []).append(event)

    if errors:
        if enforced:
            apply_failure(checkpoint, manifest, args.step, f"validation failed: {args.name}")
        else:
            checkpoint.setdefault("validation_warnings", []).append(event)
            checkpoint["last_updated"] = now_iso()
    else:
        checkpoint["last_updated"] = now_iso()
        if args.record_as:
            checkpoint["artifacts"][args.record_as] = str(artifact_path)
            record = artifact_record(
                args.record_as,
                artifact_path,
                args.step,
                Path(args.schema).resolve() if args.schema else None,
            )
            manifest["artifacts"] = [item for item in manifest["artifacts"] if item["name"] != args.record_as]
            manifest["artifacts"].append(record)
        if args.complete_step:
            checkpoint["last_completed_step"] = max(checkpoint["last_completed_step"], args.step)
            checkpoint["current_step"] = min(args.step + 1, len(manifest["steps"]))
            if checkpoint["last_completed_step"] >= len(manifest["steps"]):
                checkpoint["status"] = "completed"
            for item in manifest["steps"]:
                if item["step"] == args.step:
                    item["status"] = "completed"

    schema_errors = validate_checkpoint(checkpoint) + validate_manifest(manifest)
    if schema_errors:
        for error in schema_errors:
            print(error, file=sys.stderr)
        return 1

    write_json(checkpoint_path(args.job_id), checkpoint)
    write_json(manifest_path(args.job_id), manifest)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        if enforced:
            print(f"Validation gate BLOCKED: {args.name} ({policy})", file=sys.stderr)
            return 1
        print(f"Validation gate warning: {args.name} ({policy})")
        return 0

    print(f"Validation gate PASS: {args.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage legal translation jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Create a new translation job")
    start_parser.add_argument("--input", required=True, help="Source document path")
    start_parser.add_argument("--target", required=True, help="Target language code")
    start_parser.add_argument("--source-lang", default="unknown", help="Source language code")
    start_parser.add_argument("--mode", default="normal", choices=["fast", "normal", "hard"])
    start_parser.add_argument("--format", dest="output_format", default="docx")
    start_parser.add_argument("--library-profile", default=None)
    start_parser.add_argument("--document-type", default=None)
    start_parser.add_argument("--job-id", default=None)
    start_parser.add_argument("--retry-budget", type=int, default=1)
    start_parser.add_argument("--validation-policy", default=None, choices=sorted(VALIDATION_POLICIES))
    start_parser.add_argument("--dry-run", action="store_true")
    start_parser.set_defaults(func=start)

    status_parser = subparsers.add_parser("status", help="Show job status")
    status_parser.add_argument("--job-id", required=True)
    status_parser.set_defaults(func=status)

    resume_parser = subparsers.add_parser("resume", help="Validate and resume a job")
    resume_parser.add_argument("--job-id", required=True)
    resume_parser.add_argument("--dry-run", action="store_true")
    resume_parser.set_defaults(func=resume)

    artifact_parser = subparsers.add_parser("record-artifact", help="Record an artifact in checkpoint and manifest")
    artifact_parser.add_argument("--job-id", required=True)
    artifact_parser.add_argument("--step", type=int, required=True)
    artifact_parser.add_argument("--name", required=True)
    artifact_parser.add_argument("--path", required=True)
    artifact_parser.add_argument("--schema", default=None)
    artifact_parser.add_argument("--complete-step", action="store_true")
    artifact_parser.set_defaults(func=record_artifact)

    failure_parser = subparsers.add_parser("record-failure", help="Record a failed step and retry state")
    failure_parser.add_argument("--job-id", required=True)
    failure_parser.add_argument("--step", type=int, default=None)
    failure_parser.add_argument("--reason", required=True)
    failure_parser.set_defaults(func=record_failure)

    gate_parser = subparsers.add_parser("validate-gate", help="Validate an artifact under rollout policy")
    gate_parser.add_argument("--job-id", required=True)
    gate_parser.add_argument("--step", type=int, required=True)
    gate_parser.add_argument("--name", required=True)
    gate_parser.add_argument("--artifact", required=True)
    gate_parser.add_argument("--schema", default=None)
    gate_parser.add_argument("--expect", action="append", default=[])
    gate_parser.add_argument("--record-as", default=None)
    gate_parser.add_argument("--complete-step", action="store_true")
    gate_parser.add_argument("--validation-policy", default=None, choices=sorted(VALIDATION_POLICIES))
    gate_parser.set_defaults(func=validate_gate)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PathPolicyError as exc:
        print(f"translate-job: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
