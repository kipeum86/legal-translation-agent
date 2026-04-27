#!/usr/bin/env python3
"""CLI wrapper for context_pack.py."""

from __future__ import annotations

import sys

from context_pack import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
