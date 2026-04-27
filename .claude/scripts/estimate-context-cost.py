#!/usr/bin/env python3
"""CLI wrapper for estimate_context_cost.py."""

from __future__ import annotations

import sys

from estimate_context_cost import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
