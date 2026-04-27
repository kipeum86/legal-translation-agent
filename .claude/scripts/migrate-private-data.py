#!/usr/bin/env python3
"""Dry-run-first migration helper for repo-root private data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from private_path import PathPolicyError, private_root, repo_root


MIGRATION_TARGETS = ("config.json", "input", "output", "glossary", "_private")
LIBRARY_PUBLIC_EXCLUSIONS = {"_example", ".gitkeep"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(path: Path) -> list[dict]:
    if path.is_file():
        return [{
            "path": str(path),
            "relative_path": path.name,
            "type": "file",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }]

    entries: list[dict] = []
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        entries.append({
            "path": str(item),
            "relative_path": str(item.relative_to(path)),
            "type": "file",
            "sha256": sha256_file(item),
            "bytes": item.stat().st_size,
        })
    return entries


def inventory_signature(entries: list[dict]) -> dict[str, tuple[str, int]]:
    return {
        entry["relative_path"]: (entry["sha256"], entry["bytes"])
        for entry in entries
    }


def discover_library_moves(root: Path, private: Path) -> list[dict]:
    library = root / "library"
    if not library.exists() or not library.is_dir():
        return []

    moves = []
    for item in sorted(library.iterdir()):
        if item.name in LIBRARY_PUBLIC_EXCLUSIONS:
            continue
        moves.append({
            "name": f"library/{item.name}",
            "source": item,
            "target": private / "library" / item.name,
            "source_inventory": inventory(item),
        })
    return moves


def discover(root: Path, private: Path) -> list[dict]:
    moves = []
    for name in MIGRATION_TARGETS:
        source = root / name
        if not source.exists():
            continue
        target = private / name
        moves.append({
            "name": name,
            "source": source,
            "target": target,
            "source_inventory": inventory(source),
        })
    moves.extend(discover_library_moves(root, private))
    return moves


def write_manifest(private: Path, moves: list[dict], applied: bool) -> Path:
    manifest_dir = private / "_private" / "migration-manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"migration-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "applied": applied,
        "moves": [
            {
                "name": move["name"],
                "source": str(move["source"]),
                "target": str(move["target"]),
                "source_inventory": move["source_inventory"],
                "target_inventory": move.get("target_inventory"),
                "verified": move.get("verified"),
                "verification_errors": move.get("verification_errors", []),
            }
            for move in moves
        ],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def preflight_moves(moves: list[dict]) -> None:
    for move in moves:
        target: Path = move["target"]
        if target.exists():
            raise RuntimeError(f"Refusing to overwrite existing target: {target}")


def verify_move(move: dict) -> list[str]:
    target: Path = move["target"]
    target_inventory = inventory(target) if target.exists() else []
    move["target_inventory"] = target_inventory
    source_signature = inventory_signature(move["source_inventory"])
    target_signature = inventory_signature(target_inventory)
    errors = []
    if source_signature != target_signature:
        errors.append("source and target inventory checksums differ")
    move["verified"] = not errors
    move["verification_errors"] = errors
    return errors


def apply_moves(moves: list[dict]) -> list[str]:
    preflight_moves(moves)
    for move in moves:
        source: Path = move["source"]
        target: Path = move["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    errors = []
    for move in moves:
        errors.extend(f"{move['name']}: {error}" for error in verify_move(move))
    return errors


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Move private data out of the repo root.")
    parser.add_argument("--dry-run", action="store_true", help="Show the migration plan without moving files.")
    parser.add_argument("--apply", action="store_true", help="Actually move files. Default is dry-run.")
    args = parser.parse_args(argv)

    if args.dry_run and args.apply:
        print("migrate-private-data: choose either --dry-run or --apply, not both", file=sys.stderr)
        return 2

    root = repo_root().resolve()
    try:
        private = private_root(os.environ)
    except PathPolicyError as exc:
        print(f"migrate-private-data: {exc}", file=sys.stderr)
        return 2

    moves = discover(root, private)
    if not moves:
        print("No repo-root private data found.")
        return 0

    print("Migration plan:")
    for move in moves:
        print(f"  {move['source']} -> {move['target']}")

    if not args.apply:
        manifest = write_manifest(private, moves, applied=False)
        print(f"Dry-run only. Manifest: {manifest}")
        print("Re-run with --apply to move these paths.")
        return 0

    try:
        verification_errors = apply_moves(moves)
    except RuntimeError as exc:
        print(f"migrate-private-data: {exc}", file=sys.stderr)
        return 3

    manifest = write_manifest(private, moves, applied=True)
    if verification_errors:
        for error in verification_errors:
            print(f"migrate-private-data: verification failed: {error}", file=sys.stderr)
        print(f"Migration manifest: {manifest}")
        return 3
    print(f"Migration complete. Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
