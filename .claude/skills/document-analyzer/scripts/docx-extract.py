#!/usr/bin/env python3
"""Extract DOCX markdown plus a structured fidelity sidecar from OOXML."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Iterable


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def parse_xml(package: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        with package.open(name) as handle:
            return ET.parse(handle).getroot()
    except KeyError:
        return None
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {name}: {exc}") from exc


def iter_part_names(package: zipfile.ZipFile, prefix: str) -> Iterable[str]:
    for name in sorted(package.namelist()):
        if name.startswith(prefix) and name.endswith(".xml"):
            yield name


def element_text(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.tag in {f"{W}t", f"{W}delText"} and node.text:
            parts.append(node.text)
        elif node.tag == f"{W}tab":
            parts.append("\t")
        elif node.tag in {f"{W}br", f"{W}cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def paragraph_style(paragraph: ET.Element) -> str | None:
    style = paragraph.find(f"{W}pPr/{W}pStyle")
    if style is not None:
        return style.attrib.get(f"{W}val")
    return None


def paragraph_to_markdown(paragraph: ET.Element) -> str:
    text = element_text(paragraph)
    if not text:
        return ""
    style = paragraph_style(paragraph) or ""
    if style.lower().startswith("heading1") or style.lower() == "title":
        return f"# {text}"
    if style.lower().startswith("heading2"):
        return f"## {text}"
    if style.lower().startswith("heading3"):
        return f"### {text}"
    return text


def table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall(f".//{W}tr"):
        cells = []
        for cell in row.findall(f"{W}tc"):
            cells.append(" ".join(element_text(paragraph) for paragraph in cell.findall(f".//{W}p") if element_text(paragraph)))
        if cells:
            rows.append(cells)
    return rows


def table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    output = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for row in padded[1:]:
        output.append("| " + " | ".join(row) + " |")
    return "\n".join(output)


def extract_main_document(package: zipfile.ZipFile) -> tuple[list[str], list[dict], list[dict]]:
    root = parse_xml(package, "word/document.xml")
    if root is None:
        raise ValueError("word/document.xml not found")
    body = root.find(f"{W}body")
    if body is None:
        raise ValueError("word/document.xml has no body")

    markdown_blocks: list[str] = []
    paragraphs: list[dict] = []
    tables: list[dict] = []

    for child in body:
        if child.tag == f"{W}p":
            text = element_text(child)
            if text:
                paragraphs.append({"index": len(paragraphs) + 1, "text": text, "style": paragraph_style(child)})
                rendered = paragraph_to_markdown(child)
                if rendered:
                    markdown_blocks.append(rendered)
        elif child.tag == f"{W}tbl":
            rows = table_rows(child)
            if rows:
                tables.append({"index": len(tables) + 1, "rows": rows})
                markdown_blocks.append(table_to_markdown(rows))
    return markdown_blocks, paragraphs, tables


def extract_text_parts(package: zipfile.ZipFile, prefix: str) -> list[dict]:
    parts = []
    for name in iter_part_names(package, prefix):
        root = parse_xml(package, name)
        if root is None:
            continue
        text = element_text(root)
        if text:
            parts.append({"part": name, "text": text})
    return parts


def extract_numbered_parts(package: zipfile.ZipFile, name: str, child_tag: str) -> list[dict]:
    root = parse_xml(package, name)
    if root is None:
        return []
    items = []
    for child in root.findall(f"{W}{child_tag}"):
        item_id = child.attrib.get(f"{W}id", "")
        text = element_text(child)
        if text:
            items.append({"id": item_id, "text": text})
    return items


def tracked_changes_detected(package: zipfile.ZipFile) -> bool:
    root = parse_xml(package, "word/document.xml")
    if root is None:
        return False
    return any(node.tag in {f"{W}ins", f"{W}del", f"{W}moveFrom", f"{W}moveTo"} for node in root.iter())


def build_structure(input_path: Path, package: zipfile.ZipFile, paragraphs: list[dict], tables: list[dict]) -> dict:
    headers = extract_text_parts(package, "word/header")
    footers = extract_text_parts(package, "word/footer")
    footnotes = extract_numbered_parts(package, "word/footnotes.xml", "footnote")
    comments = extract_numbered_parts(package, "word/comments.xml", "comment")
    has_tracked_changes = tracked_changes_detected(package)
    warnings = []
    if comments:
        warnings.append("comments_detected_not_merged")
    if has_tracked_changes:
        warnings.append("tracked_changes_detected_not_merged")
    if footnotes:
        warnings.append("footnotes_extracted_to_sidecar")
    return OrderedDict(
        [
            ("schema_version", 1),
            ("format", "docx"),
            ("input_file", str(input_path)),
            ("paragraphs", paragraphs),
            ("tables", tables),
            ("headers", headers),
            ("footers", footers),
            ("footnotes", footnotes),
            ("comments", comments),
            ("tracked_changes_detected", has_tracked_changes),
            ("page_text_density", []),
            ("ocr_required_likely", False),
            ("extraction_warnings", warnings),
        ]
    )


def extract(input_path: Path, markdown_path: Path, structure_path: Path) -> dict:
    with zipfile.ZipFile(input_path) as package:
        markdown_blocks, paragraphs, tables = extract_main_document(package)
        structure = build_structure(input_path, package, paragraphs, tables)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    structure_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n\n".join(block for block in markdown_blocks if block), encoding="utf-8")
    structure_path.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
    return structure


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Extract DOCX markdown and source-structure sidecar.")
    parser.add_argument("input_docx")
    parser.add_argument("markdown_output")
    parser.add_argument("structure_output")
    args = parser.parse_args(argv)

    try:
        structure = extract(Path(args.input_docx), Path(args.markdown_output), Path(args.structure_output))
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        print(f"docx-extract: {exc}", file=sys.stderr)
        return 1
    print(
        "DOCX structure: "
        f"{len(structure['paragraphs'])} paragraphs, "
        f"{len(structure['tables'])} tables -> {args.structure_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
