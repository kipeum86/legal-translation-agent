Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Manage persistent glossaries.

Execute WF3 — Glossary Management:

Parse $ARGUMENTS for sub-command and execute:

| Sub-command | Action |
|-------------|--------|
| `list` | List all glossary files in `/glossary/` with term counts |
| `show {lang-pair}` | Display glossary contents for a language pair (e.g., `show en_ko`) |
| `search {term}` | Search across all glossaries for a term |
| `export {lang-pair} --format xlsx/csv` | Export glossary to spreadsheet format |
| `import {file}` | Import external glossary file (validate schema, merge) |
| `edit {lang-pair} {term}` | Edit a specific term mapping interactively |
| `stats` | Show usage statistics — most-used terms, stale terms, conflict history |

If no sub-command provided, default to `list`.
