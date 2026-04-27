#!/usr/bin/env python3
"""CLI wrapper for translate_batch.py."""

from __future__ import annotations

import sys

from translate_batch import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
