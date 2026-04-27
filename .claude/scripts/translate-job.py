#!/usr/bin/env python3
"""CLI wrapper for translate_job.py."""

from __future__ import annotations

import sys

from translate_job import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
