Manage Library profiles and assets.

Execute WF2 — Library Management:

Parse $ARGUMENTS for sub-command and execute:

| Sub-command | Action |
|-------------|--------|
| `list` | List all Library profiles with asset counts |
| `show {profile}` | Display profile details and asset manifest |
| `ingest {profile}` | Ingest new assets from `/library/{profile}/inbox/` — validate, classify, move to correct subfolder, update profile.json |
| `create-profile {name}` | Create new profile with empty directory structure and profile.json |
| `validate {profile}` | Validate all assets — glossary schema, file readability, style guide format |

If no sub-command provided, default to `list`.

Note: The Library is user-managed. The agent reads Library assets but never modifies reference translations, custom glossaries, or style guides directly. Only the `ingest` command moves files from inbox to their proper locations.

### Reference Ingest Flow

When ingesting reference files from inbox:

1. Ask user for the **language pair** (e.g., `en-ko`) and **role** (`source` or `target`) of each file
2. If `/library/{profile}/references/{src}-{tgt}/` does not exist, create it with `source/` and `target/` subfolders
3. Move each file to the appropriate subfolder: `references/{src}-{tgt}/source/` or `references/{src}-{tgt}/target/`
4. Update `profile.json` references array with the new language pair entry

### File Readability & Parsing

Library reference files can be any format (.docx, .pdf, .pptx, .xlsx, .html, .epub, etc.). When reading Library assets (during `validate`, `ingest`, or Step 9 comparison), use the appropriate parser:

| Format | Parser |
|--------|--------|
| `.docx` | `parse-docx.sh` (structure-optimized) |
| `.pdf` | `parse-pdf.sh` (structure-optimized) |
| `.md`, `.txt` | Direct read |
| Other formats | `parse-generic.sh` (MarkItDown → pandoc fallback) |

The `validate` sub-command should verify that each asset file can be successfully parsed to markdown using the appropriate parser above. If MarkItDown is not installed and a non-core format is encountered, warn the user with install instructions (`pip install 'markitdown[all]'`).

### create-profile Directory Structure

When creating a new profile, generate:
```
/library/{name}/
├── profile.json
├── inbox/
├── references/           # Language-pair folders created on ingest
├── glossaries/
└── style-guides/
```
