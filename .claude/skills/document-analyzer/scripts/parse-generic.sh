#!/usr/bin/env bash
# parse-generic.sh — Convert non-core document formats to Markdown via MarkItDown MCP.
#
# Purpose:
#   Handles formats NOT covered by parse-docx.sh or parse-pdf.sh:
#   .pptx, .xlsx, .html, .epub, .csv, .json, .xml, etc.
#
#   For .docx and .pdf, use the dedicated parsers (parse-docx.sh, parse-pdf.sh)
#   which have structure-preserving logic optimized for the translation pipeline.
#
# Strategy:
#   1. Try MarkItDown CLI (pip install 'markitdown[all]')
#   2. Fallback to pandoc (if format is supported)
#   3. Fail with guidance
#
# Usage:
#   bash parse-generic.sh <input_file> <output_dir>
#
# Outputs:
#   <output_dir>/source-parsed.md — Full text in markdown format

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: bash parse-generic.sh <input_file> <output_dir>"
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

run_sanitizer() {
    local sanitize_script
    sanitize_script="$(cd "$(dirname "$0")/../../ingest-sanitizer/scripts" && pwd)/sanitize.py"
    if [ -f "$sanitize_script" ]; then
        python3 "$sanitize_script" "$OUTPUT_FILE" "$OUTPUT_FILE" 2>&1 | sed 's/^/  /' || true
    fi
}

EXT="${INPUT_FILE##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

# ─── Guard: redirect core formats to dedicated parsers ────────────────────
case "$EXT_LOWER" in
    docx)
        echo "Error: Use parse-docx.sh for .docx files (better structure preservation)."
        exit 1
        ;;
    pdf)
        echo "Error: Use parse-pdf.sh for .pdf files (better structure preservation)."
        exit 1
        ;;
    md|txt)
        echo "Info: .md/.txt files can be copied directly. Copying as-is."
        cp "$INPUT_FILE" "$OUTPUT_FILE"
        run_sanitizer
        LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
        echo "  Output: $OUTPUT_FILE ($LINES lines)"
        exit 0
        ;;
esac

# ─── Method 1: MarkItDown CLI ────────────────────────────────────────────
try_markitdown() {
    if command -v markitdown &>/dev/null; then
        markitdown "$INPUT_FILE" -o "$OUTPUT_FILE" 2>/dev/null
        return $?
    fi
    return 1
}

# ─── Method 2: pandoc (limited format support) ───────────────────────────
try_pandoc() {
    if ! command -v pandoc &>/dev/null; then
        return 1
    fi

    # pandoc-supported formats that might appear in legal context
    case "$EXT_LOWER" in
        html|htm|epub|odt|rtf|rst|latex|tex)
            pandoc "$INPUT_FILE" -t markdown --wrap=none -o "$OUTPUT_FILE" 2>/dev/null
            return $?
            ;;
        *)
            return 1
            ;;
    esac
}

# ─── Execute with fallback chain ─────────────────────────────────────────
echo "Parsing generic format (.$EXT_LOWER): $INPUT_FILE"

if try_markitdown; then
    echo "  Method: markitdown"
elif try_pandoc; then
    echo "  Method: pandoc"
else
    echo "Error: Could not parse .$EXT_LOWER format."
    echo "  Install markitdown (pip install 'markitdown[all]') for broad format support."
    echo "  Alternatively, convert the file to .docx, .pdf, .md, or .txt manually."
    exit 1
fi

if [ -f "$OUTPUT_FILE" ]; then
    run_sanitizer
    LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "  Output: $OUTPUT_FILE ($LINES lines)"
else
    echo "Error: Output file was not created."
    exit 1
fi
