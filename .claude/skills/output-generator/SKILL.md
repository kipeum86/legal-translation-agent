# output-generator Skill

Assemble final translation document with appendices and convert to the user's chosen output format.

## Capabilities

1. **Document Assembly** (LLM + script)
   - Combine translation body with:
     - Term Glossary table (from working-glossary.json)
     - Structural Verification Checklist (from verification-checklist.json)
     - Translation Notes section (collected `[TN]` annotations)
     - Hard mode reports (back-translation summary, Library comparison summary, editorial change log)
   - Add header: document title, source/target language, date, mode, disclaimer

2. **Format Conversion** (`scripts/file-converter.sh`)
   - Convert assembled markdown to: TXT, MD (formatted), or DOCX
   - Fallback: pandoc → python-docx → markdown
   - Usage: `bash scripts/file-converter.sh <translation.md> <format> <output_dir> [options]`
   - Options: `--glossary`, `--checklist`, `--filename`, `--date`, `--doctype`, `--src`, `--tgt`, `--mode`

3. **File Naming**
   - Convention: `{date}_{doctype}_{src}-to-{tgt}_{mode}_v{N}.{ext}`
   - Auto-increment version number if file exists
   - Example: `2026-03-16_eula_en-to-ko_normal_v1.docx`

4. **Chat Inline Output**
   - For "chat inline" format: display full translation in chat response
   - Append glossary and checklist inline below translation
   - For long documents (>~4,000 tokens output): warn that file output may be more practical

## Workflow

```
synthesized.md + working-glossary.json + verification-checklist.json
    │
    ├── Assemble combined markdown
    │
    ├── file-converter.sh (for file formats)
    │       ↓
    └── Final output file in output/documents/
```

## When to Use

- **WF1 Step 7**: Output Assembly (Normal mode exit or Hard mode intermediate)
- **WF1 Step 10**: Final Output Assembly (Hard mode exit, after editorial polish)

## Output Format Selection

On first job of session, ask:
> "출력 형식은? (채팅 / TXT / Markdown / DOCX — 기본값: DOCX)"

Subsequent jobs:
> "이전과 같은 형식({format})? (Y / 변경)"

## Checkpoint

Step 7/10 output assembly:
- `step_7.output_format` → selected format
- `step_7.output_file` → path to final file
