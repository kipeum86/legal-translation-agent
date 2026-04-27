#!/usr/bin/env bash
# parse-docx.sh — Extract text and structure from DOCX files.
#
# Strategy:
#   1. Try python3 with python-docx (best structure preservation)
#   2. Fallback to pandoc (good markdown conversion)
#   3. Fallback to unzip + basic XML extraction
#
# Usage:
#   bash parse-docx.sh <input.docx> <output_dir>
#
# Outputs:
#   <output_dir>/source-parsed.md — Full text in markdown format
#   <output_dir>/source-structure.json — Tables, headers, footers, footnotes, comments, tracked-change flags

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: bash parse-docx.sh <input.docx> <output_dir>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PATH_RESOLVER="$REPO_ROOT/.claude/scripts/private-path.py"

resolve_path() {
    python3 "$PATH_RESOLVER" "$1"
}

INPUT_FILE="$(resolve_path "$1")"
OUTPUT_DIR="$(resolve_path "$2")"
OUTPUT_FILE="${OUTPUT_DIR}/source-parsed.md"
STRUCTURE_FILE="${OUTPUT_DIR}/source-structure.json"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found: $INPUT_FILE"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

run_sanitizer() {
    local sanitize_script
    sanitize_script="$(cd "$(dirname "$0")/../../ingest-sanitizer/scripts" && pwd)/sanitize.py"
    if [ ! -f "$sanitize_script" ]; then
        if [ "${LEGAL_TRANSLATION_ALLOW_UNSANITIZED:-}" = "1" ]; then
            echo "  Warning: sanitizer not found; continuing because LEGAL_TRANSLATION_ALLOW_UNSANITIZED=1"
            return 0
        fi
        echo "Error: Sanitizer not found: $sanitize_script"
        exit 1
    fi
    if ! python3 "$sanitize_script" "$OUTPUT_FILE" "$OUTPUT_FILE" 2>&1 | sed 's/^/  /'; then
        if [ "${LEGAL_TRANSLATION_ALLOW_UNSANITIZED:-}" = "1" ]; then
            echo "  Warning: sanitizer failed; continuing because LEGAL_TRANSLATION_ALLOW_UNSANITIZED=1"
            return 0
        fi
        echo "Error: Sanitizer failed. Set LEGAL_TRANSLATION_ALLOW_UNSANITIZED=1 only for an explicit bypass."
        exit 1
    fi
}

# ─── Method 1: OOXML direct extraction ──────────────────────────────────
try_ooxml_extract() {
    python3 "$SCRIPT_DIR/docx-extract.py" "$INPUT_FILE" "$OUTPUT_FILE" "$STRUCTURE_FILE" 2>/dev/null
}

# ─── Method 2: python-docx ───────────────────────────────────────────────
try_python_docx() {
    python3 -c "
import sys
try:
    from docx import Document
except ImportError:
    sys.exit(1)

doc = Document('$INPUT_FILE')
lines = []

for para in doc.paragraphs:
    style = para.style.name if para.style else ''
    text = para.text.strip()
    if not text:
        lines.append('')
        continue

    # Convert heading styles to markdown
    if 'Heading 1' in style:
        lines.append(f'# {text}')
    elif 'Heading 2' in style:
        lines.append(f'## {text}')
    elif 'Heading 3' in style:
        lines.append(f'### {text}')
    elif 'Heading 4' in style:
        lines.append(f'#### {text}')
    else:
        # Check for bold runs (may indicate section headers)
        has_bold = any(run.bold for run in para.runs if run.text.strip())
        all_bold = all(run.bold for run in para.runs if run.text.strip()) if para.runs else False
        if all_bold and len(text) < 200:
            lines.append(f'**{text}**')
        else:
            lines.append(text)

    lines.append('')

for table in doc.tables:
    rows = []
    for row in table.rows:
        rows.append([cell.text.strip().replace('\n', ' ') for cell in row.cells])
    if rows:
        width = max(len(row) for row in rows)
        rows = [row + [''] * (width - len(row)) for row in rows]
        lines.append('| ' + ' | '.join(rows[0]) + ' |')
        lines.append('| ' + ' | '.join('---' for _ in rows[0]) + ' |')
        for row in rows[1:]:
            lines.append('| ' + ' | '.join(row) + ' |')
        lines.append('')

with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
" 2>/dev/null
}

# ─── Method 3: pandoc ────────────────────────────────────────────────────
try_pandoc() {
    if command -v pandoc &>/dev/null; then
        pandoc "$INPUT_FILE" -t markdown --wrap=none -o "$OUTPUT_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# ─── Method 4: Basic XML extraction ─────────────────────────────────────
try_xml_extract() {
    python3 -c "
import zipfile
import xml.etree.ElementTree as ET

WORD_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

with zipfile.ZipFile('$INPUT_FILE', 'r') as z:
    with z.open('word/document.xml') as f:
        tree = ET.parse(f)

root = tree.getroot()
body = root.find(f'{WORD_NS}body')
lines = []

for para in body.iter(f'{WORD_NS}p'):
    texts = []
    for run in para.iter(f'{WORD_NS}r'):
        t = run.find(f'{WORD_NS}t')
        if t is not None and t.text:
            texts.append(t.text)
    line = ''.join(texts).strip()
    lines.append(line)

with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(line for line in lines if line))
" 2>/dev/null
}

# ─── Execute with fallback chain ─────────────────────────────────────────
echo "Parsing DOCX: $INPUT_FILE"

if try_ooxml_extract; then
    echo "  Method: OOXML direct extraction"
elif try_python_docx; then
    echo "  Method: python-docx"
elif try_pandoc; then
    echo "  Method: pandoc"
elif try_xml_extract; then
    echo "  Method: XML extraction (basic)"
else
    echo "Error: All parsing methods failed for $INPUT_FILE"
    echo "  Install python-docx (pip install python-docx) or pandoc for best results."
    exit 1
fi

if [ -f "$OUTPUT_FILE" ]; then
    if [ ! -f "$STRUCTURE_FILE" ]; then
        python3 "$SCRIPT_DIR/docx-extract.py" "$INPUT_FILE" "$OUTPUT_FILE" "$STRUCTURE_FILE" >/dev/null 2>&1 || true
    fi
    run_sanitizer
    LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "  Output: $OUTPUT_FILE ($LINES lines)"
    if [ -f "$STRUCTURE_FILE" ]; then
        echo "  Structure: $STRUCTURE_FILE"
    fi
else
    echo "Error: Output file was not created."
    exit 1
fi
