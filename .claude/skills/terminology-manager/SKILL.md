# terminology-manager Skill

> Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
> path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Extract defined terms, manage glossary hierarchy, assemble working glossaries, and persist glossary after translation.

## Capabilities

1. **Term Extraction** (LLM judgment)
   - Identify all defined terms from source text
   - Detect definition patterns per language:
     - EN: `"Term"`, `"Term" means...`, `hereinafter referred to as`
     - KO: `이하 'X'라 한다`, `이하 "X"이라 한다`
     - ZH-CN: `以下简称"X"`, `以下称为"X"`
     - ZH-TW: `以下簡稱「X」`
     - JA: `以下「X」という`, `以下「X」といいます`
   - For each term: propose target-language equivalent with rationale

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
   - Log any Library override conflicts
   - Schema per entry: see `references/glossary-schema.md`

4. **Glossary Persistence** (`scripts/glossary-merger.py`)
   - Merge working glossary into persistent glossary after translation completes
   - New terms appended; existing terms update `last_used` + `usage_count`
   - Conflicts logged to `/glossary/conflicts.log` (keep persistent version)
   - Library-origin entries skipped (never persisted)
   - Usage: `python3 scripts/glossary-merger.py <working-glossary.json> <glossary_dir>`

5. **Glossary CRUD** (WF3 commands)
   - list, show, search, export, import, edit, stats
   - Invoked via `/glossary` command

## Workflow

```
Step 2: Glossary Setup
    │
    ├── Load persistent glossary (if exists)
    ├── Load Library custom glossary (if profile active)
    ├── Extract defined terms from source
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
- **WF1 Step 7**: Glossary persistence (always, even if Hard mode steps fail)
- **WF3**: Glossary management commands

## Failure Handling

- Term ambiguity → insert `[TN: {explanation}]` flag, proceed; resolve during synthesis
- Persistent glossary file not found → create new (first translation for this language pair)
- Merge conflict → keep persistent version, log to conflicts.log

## Checkpoint

Step 2 completion:
- `step_2.status` → `"completed"`
- `step_2.outputs` → `["working-glossary.json"]`
- `last_completed_step` → `2`
