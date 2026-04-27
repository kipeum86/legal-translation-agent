#!/usr/bin/env python3
"""Resolve user-data paths into LEGAL_TRANSLATION_PRIVATE_DIR.

This module keeps repo-relative private paths such as input/, output/,
library/, glossary/, and _private/ from accidentally being created under the
public repository root.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


MANAGED_ROOTS = {"input", "output", "library", "glossary", "_private"}
PUBLIC_REPO_EXCEPTIONS = (Path("library") / "_example",)


class PathPolicyError(ValueError):
    """Raised when a path violates the private-data policy."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _clean_relative_parts(path: Path) -> tuple[str, ...]:
    return tuple(part for part in path.parts if part not in ("", "."))


def _is_public_repo_exception(relative_path: Path) -> bool:
    return any(
        relative_path == exception or _is_relative_to(relative_path, exception)
        for exception in PUBLIC_REPO_EXCEPTIONS
    )


def private_root(env: dict[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    raw = env.get("LEGAL_TRANSLATION_PRIVATE_DIR", "").strip()
    if not raw:
        raise PathPolicyError(
            "LEGAL_TRANSLATION_PRIVATE_DIR is not set. "
            "Set it before using input/, output/, library/, glossary/, or _private/ paths."
        )
    return Path(raw).expanduser().resolve()


def resolve_private_path(
    raw_path: str,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    require_private_root: bool = False,
) -> Path:
    """Resolve a path according to the agent's private-directory policy."""

    env = os.environ if env is None else env
    cwd = (cwd or Path.cwd()).resolve()
    root = repo_root().resolve()
    path = Path(raw_path).expanduser()

    if require_private_root:
        private_root(env)

    if path.is_absolute():
        resolved = path.resolve()
        if _is_relative_to(resolved, root):
            relative = resolved.relative_to(root)
            parts = relative.parts
            if parts and parts[0] in MANAGED_ROOTS and not _is_public_repo_exception(relative):
                raise PathPolicyError(
                    f"Refusing repo-internal private-data path: {resolved}. "
                    "Use LEGAL_TRANSLATION_PRIVATE_DIR-backed paths instead."
                )
        return resolved

    parts = _clean_relative_parts(path)
    if parts and parts[0] in MANAGED_ROOTS:
        relative = Path(*parts)
        if _is_public_repo_exception(relative):
            return (root / relative).resolve()
        return (private_root(env) / relative).resolve()

    return (cwd / path).resolve()


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Resolve legal-translation-agent data paths.")
    parser.add_argument("path", help="Path to resolve")
    parser.add_argument(
        "--require-private-root",
        action="store_true",
        help="Fail if LEGAL_TRANSLATION_PRIVATE_DIR is not set, even for non-managed paths.",
    )
    args = parser.parse_args(argv)

    try:
        print(resolve_private_path(args.path, require_private_root=args.require_private_root))
    except PathPolicyError as exc:
        print(f"private-path: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
