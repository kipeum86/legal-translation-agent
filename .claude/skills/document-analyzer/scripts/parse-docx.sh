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

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: bash parse-docx.sh <input.docx> <output_dir>"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_DIR="$2"
OUTPUT_FILE="${OUTPUT_DIR}/source-parsed.md"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found: $INPUT_FILE"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# ─── Method 1: python-docx ───────────────────────────────────────────────
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

with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
" 2>/dev/null
}

# ─── Method 2: pandoc ────────────────────────────────────────────────────
try_pandoc() {
    if command -v pandoc &>/dev/null; then
        pandoc "$INPUT_FILE" -t markdown --wrap=none -o "$OUTPUT_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# ─── Method 3: Basic XML extraction ─────────────────────────────────────
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

if try_python_docx; then
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
    LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "  Output: $OUTPUT_FILE ($LINES lines)"
else
    echo "Error: Output file was not created."
    exit 1
fi
