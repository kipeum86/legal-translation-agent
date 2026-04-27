#!/usr/bin/env python3
"""Run the local release checks used by CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable or "python3"

PYTEST_TARGETS = [
    ".claude/scripts/tests",
    ".claude/skills/document-analyzer/scripts/tests",
    ".claude/skills/structural-verifier/scripts/tests",
    ".claude/skills/ingest-sanitizer/scripts/tests",
    ".claude/skills/terminology-manager/scripts/tests",
    ".claude/skills/output-generator/scripts/tests",
]

PY_COMPILE_PATTERNS = [
    ".claude/scripts/*.py",
    ".claude/skills/document-analyzer/scripts/*.py",
    ".claude/skills/structural-verifier/scripts/count-comparator.py",
    ".claude/skills/terminology-manager/scripts/*.py",
    ".claude/skills/output-generator/scripts/*.py",
]

BASH_SYNTAX_TARGETS = [
    ".claude/skills/document-analyzer/scripts/parse-docx.sh",
    ".claude/skills/document-analyzer/scripts/parse-pdf.sh",
    ".claude/skills/document-analyzer/scripts/parse-generic.sh",
    ".claude/skills/output-generator/scripts/file-converter.sh",
]


@dataclass(frozen=True)
class CheckCommand:
    name: str
    argv: list[str]


def expand_patterns(patterns: list[str]) -> list[str]:
    paths: list[str] = []
    for pattern in patterns:
        matches = sorted(REPO_ROOT.glob(pattern))
        if not matches:
            raise FileNotFoundError(f"check pattern matched no files: {pattern}")
        paths.extend(str(path.relative_to(REPO_ROOT)) for path in matches if path.is_file())
    return sorted(dict.fromkeys(paths))


def existing_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if (REPO_ROOT / path).exists()]


def build_commands(*, skip_regression: bool = False) -> list[CheckCommand]:
    commands: list[CheckCommand] = []
    if not skip_regression:
        commands.append(
            CheckCommand(
                "dry-run regression",
                [PYTHON, ".claude/scripts/run-regression.py"],
            )
        )

    pytest_targets = existing_paths(PYTEST_TARGETS)
    if pytest_targets:
        commands.append(
            CheckCommand(
                "pytest",
                [PYTHON, "-m", "pytest", *pytest_targets, "-q"],
            )
        )

    commands.append(
        CheckCommand(
            "python syntax",
            [PYTHON, "-m", "py_compile", *expand_patterns(PY_COMPILE_PATTERNS)],
        )
    )

    bash_targets = existing_paths(BASH_SYNTAX_TARGETS)
    if bash_targets:
        commands.append(
            CheckCommand(
                "shell syntax",
                ["bash", "-n", *bash_targets],
            )
        )

    return commands


def run_command(command: CheckCommand) -> int:
    print(f"\n==> {command.name}", flush=True)
    result = subprocess.run(command.argv, cwd=REPO_ROOT, check=False)
    if result.returncode == 0:
        print(f"PASS: {command.name}", flush=True)
    else:
        print(f"FAIL: {command.name} exited with {result.returncode}", file=sys.stderr)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local release checks.")
    parser.add_argument(
        "--skip-regression",
        action="store_true",
        help="Skip the dry-run regression gate and run only static/unit checks.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the commands without executing them.",
    )
    args = parser.parse_args(argv)

    try:
        commands = build_commands(skip_regression=args.skip_regression)
    except FileNotFoundError as exc:
        print(f"check: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for command in commands:
            print(f"{command.name}: {' '.join(command.argv)}")
        return 0

    for command in commands:
        status = run_command(command)
        if status != 0:
            return status
    print("\nAll checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
