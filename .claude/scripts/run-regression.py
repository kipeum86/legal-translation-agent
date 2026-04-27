#!/usr/bin/env python3
"""CLI wrapper for run_regression.py."""

from __future__ import annotations

import sys

from run_regression import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
