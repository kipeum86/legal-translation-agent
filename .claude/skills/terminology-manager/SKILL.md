# terminology-manager Skill

> Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
> path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Extract defined terms, manage glossary hierarchy, assemble working glossaries, and persist glossary after translation.

## Capabilities

1. **Term Candidate Extraction** (`scripts/extract-term-candidates.py` + LLM refinement)
   - Deterministically identify defined-term candidates from source text
   - Detect definition patterns per language:
     - EN: `"Term"`, `"Term" means...`, `hereinafter referred to as`
     - KO: `이하 'X'라 한다`, `이하 "X"이라 한다`
     - ZH-CN: `以下简称"X"`, `以下称为"X"`
     - ZH-TW: `以下簡稱「X」`
     - JA: `以下「X」という`, `以下「X」といいます`
   - LLM classifies candidates and proposes target-language equivalents with rationale
   - Usage: `python3 scripts/extract-term-candidates.py <source.md> <source_lang> <output.json>`

2. **Glossary Hierarchy Loading**
   - Load persistent glossary from `/glossary/glossary_{src}_{tgt}.json`
   - Load Library custom glossary from `/library/{profile}/glossaries/terms_{src}-{tgt}.json`
   - **Priority (conflict resolution order)**:
     1. Library custom glossary — highest (company-specific)
     2. Persistent glossary — accumulated from prior translations
     3. LLM proposal — when no prior mapping exists
   - Library override entries marked with `origin: "library"` in working glossary

3. **Working Glossary Assembly**
   - Merge all sources into `output/working/working-glossary.json`
   - Validate: no term maps to two different translations
   - Log any Library override conflicts and write `output/working/glossary-conflicts-queue.json`
   - Schema per entry: see `references/glossary-schema.md`

4. **Glossary Usage Check** (`scripts/check-glossary-usage.py`)
   - Verify locked glossary terms from source are present in the translation
   - Outputs `output/working/glossary-usage-report.json`
   - Any missing target term is a blocking quality-gate failure
   - Usage: `python3 scripts/check-glossary-usage.py <source.md> <translation.md> <working-glossary.json> <output.json>`

5. **Glossary Persistence** (`scripts/glossary-merger.py`)
   - Merge working glossary into persistent glossary after translation completes
   - New terms appended; existing terms update `last_used` + `usage_count`
   - Conflicts logged to `/glossary/conflicts.log` (keep persistent version)
   - Conflicts also written to `output/working/glossary-conflicts-queue.json` for user review
   - Library-origin entries skipped (never persisted)
   - Usage: `python3 scripts/glossary-merger.py <working-glossary.json> <glossary_dir>`

6. **Glossary CRUD** (WF3 commands)
   - list, show, search, export, import, edit, stats
   - Invoked via `/glossary` command

## Workflow

```
Step 2: Glossary Setup
    │
    ├── Load persistent glossary (if exists)
    ├── Load Library custom glossary (if profile active)
    ├── Extract deterministic term candidates from source
    ├── LLM reviews/refines candidates
    ├── Apply hierarchy: Library > persistent > LLM
    │       ↓
    └── working-glossary.json

Step 7: Glossary Persistence
    │
    ├── glossary-merger.py
    │       ↓
    └── Updated /glossary/glossary_{src}_{tgt}.json
```

## When to Use

- **WF1 Step 2**: Terminology Extraction & Glossary Setup
- **WF1 Step 7**: Glossary usage check before delivery
- **WF1 Step 7**: Glossary persistence (always, even if Hard mode steps fail)
- **WF3**: Glossary management commands

## Failure Handling

- Term ambiguity → insert `[TN: {explanation}]` flag, proceed; resolve during synthesis
- Glossary usage FAIL → remediate translation before delivery
- Persistent glossary file not found → create new (first translation for this language pair)
- Merge conflict → keep persistent version, log to conflicts.log, add review queue entry

## Checkpoint

Step 2 completion:
- `step_2.status` → `"completed"`
- `step_2.outputs` → `["working-glossary.json"]`
- `last_completed_step` → `2`
