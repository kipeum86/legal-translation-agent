#!/usr/bin/env python3
"""Write PDF extraction-density sidecar and OCR heuristics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path


def pages_from_pymupdf(input_path: Path) -> list[str] | None:
    try:
        import fitz  # type: ignore
    except ImportError:
        return None
    try:
        doc = fitz.open(input_path)
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return pages
    except Exception:
        return None


def pages_from_parsed_text(parsed_path: Path) -> list[str]:
    text = parsed_path.read_text(encoding="utf-8") if parsed_path.exists() else ""
    pages = text.split("\f")
    return pages if pages else [text]


def build_structure(input_path: Path, parsed_path: Path) -> dict:
    pages = pages_from_pymupdf(input_path) or pages_from_parsed_text(parsed_path)
    density = []
    warnings = []
    for index, text in enumerate(pages, 1):
        char_count = len(text.strip())
        density.append({"page": index, "char_count": char_count})
        if char_count < 40:
            warnings.append(f"low_text_density_page_{index}")
    total_chars = sum(item["char_count"] for item in density)
    ocr_likely = total_chars < 80 or bool(density and all(item["char_count"] < 40 for item in density))
    if ocr_likely:
        warnings.append("ocr_required_likely")
    return OrderedDict(
        [
            ("schema_version", 1),
            ("format", "pdf"),
            ("input_file", str(input_path)),
            ("paragraphs", []),
            ("tables", []),
            ("headers", []),
            ("footers", []),
            ("footnotes", []),
            ("comments", []),
            ("tracked_changes_detected", False),
            ("page_text_density", density),
            ("ocr_required_likely", ocr_likely),
            ("extraction_warnings", sorted(set(warnings))),
        ]
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate PDF source-structure sidecar.")
    parser.add_argument("input_pdf")
    parser.add_argument("parsed_markdown")
    parser.add_argument("structure_output")
    args = parser.parse_args(argv)

    try:
        structure = build_structure(Path(args.input_pdf), Path(args.parsed_markdown))
        output_path = Path(args.structure_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"pdf-structure: {exc}", file=sys.stderr)
        return 1
    print(f"PDF structure: {len(structure['page_text_density'])} pages -> {args.structure_output}")
    if structure["ocr_required_likely"]:
        print("PDF structure warning: OCR likely required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
