#!/usr/bin/env python3
"""CLI wrapper for private_path.py."""

from __future__ import annotations

import sys

from private_path import _cli


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
