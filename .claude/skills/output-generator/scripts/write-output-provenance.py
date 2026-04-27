#!/usr/bin/env python3
"""CLI wrapper for write_output_provenance.py."""

from __future__ import annotations

import sys

from write_output_provenance import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
