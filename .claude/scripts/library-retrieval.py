#!/usr/bin/env python3
"""CLI wrapper for library_retrieval.py."""

from __future__ import annotations

import sys

from library_retrieval import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
