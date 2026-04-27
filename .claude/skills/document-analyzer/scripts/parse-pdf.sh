#!/usr/bin/env bash
# parse-pdf.sh — Extract text from PDF files.
#
# Strategy:
#   1. Try pymupdf (best quality, preserves structure)
#   2. Fallback to pdftotext (poppler)
#   3. Fallback to pandoc
#
# Usage:
#   bash parse-pdf.sh <input.pdf> <output_dir>
#
# Outputs:
#   <output_dir>/source-parsed.md — Full text in markdown-ish format
#   <output_dir>/source-structure.json — page density and OCR heuristics

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: bash parse-pdf.sh <input.pdf> <output_dir>"
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

# ─── Method 1: pymupdf ──────────────────────────────────────────────────
try_pymupdf() {
    python3 -c "
import sys
try:
    import fitz  # pymupdf
except ImportError:
    sys.exit(1)

doc = fitz.open('$INPUT_FILE')
lines = []
for page_num, page in enumerate(doc, 1):
    text = page.get_text('text')
    if text.strip():
        lines.append(text)
doc.close()

with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(lines))
" 2>/dev/null
}

# ─── Method 2: pdftotext (poppler) ──────────────────────────────────────
try_pdftotext() {
    if command -v pdftotext &>/dev/null; then
        pdftotext -layout "$INPUT_FILE" "$OUTPUT_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# ─── Method 3: pandoc ────────────────────────────────────────────────────
try_pandoc() {
    if command -v pandoc &>/dev/null; then
        pandoc "$INPUT_FILE" -t markdown --wrap=none -o "$OUTPUT_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# ─── Execute with fallback chain ─────────────────────────────────────────
echo "Parsing PDF: $INPUT_FILE"

if try_pymupdf; then
    echo "  Method: pymupdf"
elif try_pdftotext; then
    echo "  Method: pdftotext (poppler)"
elif try_pandoc; then
    echo "  Method: pandoc"
else
    echo "Error: All parsing methods failed for $INPUT_FILE"
    echo "  Install pymupdf (pip install pymupdf), poppler (pdftotext), or pandoc."
    exit 1
fi

if [ -f "$OUTPUT_FILE" ]; then
    run_sanitizer
    python3 "$SCRIPT_DIR/pdf-structure.py" "$INPUT_FILE" "$OUTPUT_FILE" "$STRUCTURE_FILE"
    LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "  Output: $OUTPUT_FILE ($LINES lines)"
    echo "  Structure: $STRUCTURE_FILE"
else
    echo "Error: Output file was not created."
    exit 1
fi
