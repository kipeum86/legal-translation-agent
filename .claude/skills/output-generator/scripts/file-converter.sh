#!/usr/bin/env bash
# file-converter.sh — Convert markdown translation to output format.
#
# Assembles the final document by combining:
#   - Translation body (markdown)
#   - Term glossary table
#   - Structural verification checklist
#   - Translation notes
#
# Then converts to the target format (txt/md/docx).
#
# Usage:
#   bash file-converter.sh <translation.md> <output_format> <output_dir> [options]
#
# Arguments:
#   translation.md  — Path to the synthesized translation (markdown)
#   output_format   — One of: txt, md, docx
#   output_dir      — Directory for final output
#
# Options:
#   --glossary <path>     — Path to working-glossary.json (appends glossary table)
#   --checklist <path>    — Path to verification-checklist.json (appends checklist)
#   --filename <name>     — Override output filename (without extension)
#   --date <YYYY-MM-DD>   — Date for filename (default: today)
#   --doctype <type>      — Document type for filename (e.g., eula, nda, tos)
#   --src <lang>          — Source language code
#   --tgt <lang>          — Target language code
#   --mode <fast|normal|hard>  — Translation mode
#   --job-id <id>         — Translation job id for manifest recording
#   --step <number>       — Producing step for manifest recording (default: 7)

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: bash file-converter.sh <translation.md> <output_format> <output_dir> [options]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PATH_RESOLVER="$REPO_ROOT/.claude/scripts/private-path.py"

resolve_path() {
    python3 "$PATH_RESOLVER" "$1"
}

TRANSLATION="$(resolve_path "$1")"
FORMAT="$2"
OUTPUT_DIR="$(resolve_path "$3")"
shift 3

# Defaults
GLOSSARY=""
CHECKLIST=""
FILENAME=""
FILE_DATE=$(date +%Y-%m-%d)
DOCTYPE="document"
SRC="src"
TGT="tgt"
MODE="normal"
JOB_ID=""
STEP="7"

# Parse options
while [ $# -gt 0 ]; do
    case "$1" in
        --glossary)   GLOSSARY="$2"; shift 2 ;;
        --checklist)  CHECKLIST="$2"; shift 2 ;;
        --filename)   FILENAME="$2"; shift 2 ;;
        --date)       FILE_DATE="$2"; shift 2 ;;
        --doctype)    DOCTYPE="$2"; shift 2 ;;
        --src)        SRC="$2"; shift 2 ;;
        --tgt)        TGT="$2"; shift 2 ;;
        --mode)       MODE="$2"; shift 2 ;;
        --job-id)     JOB_ID="$2"; shift 2 ;;
        --step)       STEP="$2"; shift 2 ;;
        *)            echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -n "$GLOSSARY" ]; then
    GLOSSARY="$(resolve_path "$GLOSSARY")"
fi

if [ -n "$CHECKLIST" ]; then
    CHECKLIST="$(resolve_path "$CHECKLIST")"
fi

if [ ! -f "$TRANSLATION" ]; then
    echo "Error: Translation file not found: $TRANSLATION"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# ─── Generate filename ───────────────────────────────────────────────────
if [ -z "$FILENAME" ]; then
    # Find next version number
    VERSION=1
    while [ -f "${OUTPUT_DIR}/${FILE_DATE}_${DOCTYPE}_${SRC}-to-${TGT}_${MODE}_v${VERSION}.${FORMAT}" ]; do
        VERSION=$((VERSION + 1))
    done
    FILENAME="${FILE_DATE}_${DOCTYPE}_${SRC}-to-${TGT}_${MODE}_v${VERSION}"
fi

OUTPUT_FILE="${OUTPUT_DIR}/${FILENAME}.${FORMAT}"
ACTUAL_OUTPUT_FILE="$OUTPUT_FILE"
ACTUAL_FORMAT="$FORMAT"

# ─── Assemble combined markdown ──────────────────────────────────────────
ASSEMBLED=$(mktemp "${OUTPUT_DIR}/assembled-XXXXXX.md")
trap 'rm -f "$ASSEMBLED"' EXIT

# Copy translation body
cat "$TRANSLATION" > "$ASSEMBLED"

# Append glossary table if provided
if [ -n "$GLOSSARY" ] && [ -f "$GLOSSARY" ]; then
    echo "" >> "$ASSEMBLED"
    echo "---" >> "$ASSEMBLED"
    echo "" >> "$ASSEMBLED"
    echo "## Term Glossary / 용어집" >> "$ASSEMBLED"
    echo "" >> "$ASSEMBLED"

    python3 -c "
import json, sys

data = json.load(open('$GLOSSARY', encoding='utf-8'))
entries = data.get('entries', data) if isinstance(data, dict) else data

if entries:
    print('| Source Term | Target Term | Context |')
    print('|------------|-------------|---------|')
    for e in entries:
        src = e.get('source_term', '')
        tgt = e.get('target_term', '')
        ctx = e.get('context', '')
        print(f'| {src} | {tgt} | {ctx} |')
" >> "$ASSEMBLED" 2>/dev/null || echo "*Glossary rendering failed*" >> "$ASSEMBLED"
fi

# Append verification checklist if provided
if [ -n "$CHECKLIST" ] && [ -f "$CHECKLIST" ]; then
    echo "" >> "$ASSEMBLED"
    echo "---" >> "$ASSEMBLED"
    echo "" >> "$ASSEMBLED"
    echo "## Structural Verification Checklist / 구조 검증 체크리스트" >> "$ASSEMBLED"
    echo "" >> "$ASSEMBLED"

    python3 -c "
import json

data = json.load(open('$CHECKLIST', encoding='utf-8'))
overall = data.get('overall_status', 'UNKNOWN')
icon = '✅' if overall == 'PASS' else '❌'
print(f'**Overall: {icon} {overall}**')
print()
print('| Article | Source Sub-clauses | Target Sub-clauses | Status |')
print('|---------|-------------------|-------------------|--------|')
for a in data.get('article_details', []):
    art = a.get('article', '')
    s_sc = a.get('source_sub_clauses', 0)
    t_sc = a.get('target_sub_clauses', 0)
    status = '✅' if a.get('status') == 'PASS' else '❌'
    print(f'| {art} | {s_sc} | {t_sc} | {status} |')
" >> "$ASSEMBLED" 2>/dev/null || echo "*Checklist rendering failed*" >> "$ASSEMBLED"
fi

# ─── Convert to target format ────────────────────────────────────────────
case "$FORMAT" in
    txt)
        # Strip markdown formatting for plain text
        python3 -c "
import re
text = open('$ASSEMBLED', encoding='utf-8').read()
# Remove markdown formatting
text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # Headers
text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)               # Bold
text = re.sub(r'\*([^*]+)\*', r'\1', text)                    # Italic
text = re.sub(r'^\|.*\|$', lambda m: m.group().replace('|', '\t'), text, flags=re.MULTILINE)
print(text)
" > "$OUTPUT_FILE"
        echo "Output (TXT): $OUTPUT_FILE"
        ;;

    md)
        cp "$ASSEMBLED" "$OUTPUT_FILE"
        echo "Output (Markdown): $OUTPUT_FILE"
        ;;

    docx)
        if command -v pandoc &>/dev/null; then
            pandoc "$ASSEMBLED" -o "$OUTPUT_FILE" \
                --from markdown \
                -V geometry:a4paper \
                -V mainfont="Noto Sans CJK" \
                2>/dev/null
            echo "Output (DOCX via pandoc): $OUTPUT_FILE"
        elif python3 -c "import docx" 2>/dev/null; then
            # Fallback to python-docx
            python3 -c "
from docx import Document
from docx.shared import Pt

doc = Document()
with open('$ASSEMBLED', encoding='utf-8') as f:
    for line in f:
        line = line.rstrip()
        if line.startswith('# '):
            doc.add_heading(line[2:], level=1)
        elif line.startswith('## '):
            doc.add_heading(line[3:], level=2)
        elif line.startswith('### '):
            doc.add_heading(line[4:], level=3)
        elif line.startswith('---'):
            doc.add_page_break()
        elif line.strip():
            doc.add_paragraph(line)
doc.save('$OUTPUT_FILE')
"
            echo "Output (DOCX via python-docx): $OUTPUT_FILE"
        else
            # Fallback: save as markdown with .md extension instead
            FALLBACK="${OUTPUT_DIR}/${FILENAME}.md"
            cp "$ASSEMBLED" "$FALLBACK"
            ACTUAL_OUTPUT_FILE="$FALLBACK"
            ACTUAL_FORMAT="md"
            echo "Warning: pandoc and python-docx not available. Saved as Markdown instead."
            echo "Output (Markdown fallback): $FALLBACK"
        fi
        ;;

    *)
        echo "Error: Unsupported format '$FORMAT'. Use: txt, md, docx"
        exit 1
        ;;
esac

PROVENANCE_FILE="${ACTUAL_OUTPUT_FILE}.provenance.json"
PROVENANCE_ARGS=(
    --translation "$TRANSLATION"
    --output "$ACTUAL_OUTPUT_FILE"
    --provenance "$PROVENANCE_FILE"
    --format "$ACTUAL_FORMAT"
    --mode "$MODE"
)

if [ -n "$JOB_ID" ]; then
    PROVENANCE_ARGS+=(--job-id "$JOB_ID")
fi
if [ -n "$GLOSSARY" ]; then
    PROVENANCE_ARGS+=(--glossary "$GLOSSARY")
fi
if [ -n "$CHECKLIST" ]; then
    PROVENANCE_ARGS+=(--checklist "$CHECKLIST")
fi

if [ -n "$JOB_ID" ]; then
    python3 "$REPO_ROOT/.claude/scripts/translate-job.py" record-artifact \
        --job-id "$JOB_ID" \
        --step "$STEP" \
        --name final_output \
        --path "$ACTUAL_OUTPUT_FILE"
fi

python3 "$SCRIPT_DIR/write-output-provenance.py" "${PROVENANCE_ARGS[@]}"

if [ -n "$JOB_ID" ]; then
    python3 "$REPO_ROOT/.claude/scripts/translate-job.py" record-artifact \
        --job-id "$JOB_ID" \
        --step "$STEP" \
        --name output_provenance \
        --path "$PROVENANCE_FILE" \
        --schema "$REPO_ROOT/.claude/schemas/output-provenance.schema.json"
fi
