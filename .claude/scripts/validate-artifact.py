#!/usr/bin/env python3
"""CLI wrapper for validate_artifact.py."""

from __future__ import annotations

import sys

from validate_artifact import _cli


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
