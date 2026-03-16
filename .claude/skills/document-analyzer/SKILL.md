# document-analyzer Skill

Parse source documents to extract text, detect language, build structural inventory, and determine segmentation strategy.

## Capabilities

1. **DOCX Parsing** (`scripts/parse-docx.sh`)
   - Extracts full text with heading hierarchy preserved as markdown
   - Fallback chain: python-docx → pandoc → XML extraction
   - Usage: `bash scripts/parse-docx.sh <docx_path> <output_dir>`
   - Outputs: `source-parsed.md`

2. **PDF Parsing** (`scripts/parse-pdf.sh`)
   - Extracts full text from PDF documents
   - Fallback chain: pymupdf → pdftotext → pandoc
   - Usage: `bash scripts/parse-pdf.sh <pdf_path> <output_dir>`
   - Outputs: `source-parsed.md`

3. **Markdown/TXT Ingestion**
   - Copy `.md` or `.txt` files directly to `output/working/source-parsed.md`
   - No script needed — direct file copy

4. **Structural Counting** (`scripts/structural-counter.py`)
   - Deterministic article/sub-clause/enumerated-item/defined-term/footnote counting
   - Supports 5 languages: EN, KO, ZH-CN, ZH-TW, JA with language-specific patterns
   - Usage: `python3 scripts/structural-counter.py <source-parsed.md> <language_code> <output_path>`
   - Outputs: `structural-inventory.json`

5. **Language Detection** (LLM judgment)
   - Auto-detect source language from parsed text
   - If confidence < 95%, ask user to confirm
   - Identify document type: EULA, NDA, Privacy Policy, ToS, contract, etc.

6. **Segmentation Decision** (included in structural-counter.py)
   - Documents ≤ ~8,000 estimated tokens → translate as single unit
   - Documents > ~8,000 tokens → segment by article boundaries
   - Output includes segment plan in structural-inventory.json

## Workflow

```
Source file (docx/pdf/md/txt)
    │
    ├── parse-docx.sh / parse-pdf.sh / direct copy
    │       ↓
    │   source-parsed.md
    │
    └── structural-counter.py
            ↓
        structural-inventory.json
            (includes segmentation plan if needed)
```

## When to Use

- **WF1 Step 1**: Document Ingestion & Analysis
- Input: source document file path from `input/`
- Must complete before Step 2 (terminology extraction)

## Failure Handling

- Parse failure → try all fallback methods → if all fail, escalate to user with diagnostic
- Language detection ambiguity → ask user: "원문 언어를 확인해 주세요: {detected} (맞으면 Y, 아니면 언어 코드 입력)"
- Empty document → halt with error message
- Structural counter failure → proceed with LLM-based manual count as fallback

## Checkpoint

After successful completion, update `output/working/checkpoint.json`:
- `step_1.status` → `"completed"`
- `step_1.outputs` → `["source-parsed.md", "structural-inventory.json"]`
- `last_completed_step` → `1`
