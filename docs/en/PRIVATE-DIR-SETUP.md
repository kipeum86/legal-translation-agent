# Private Directory Setup

All user data for this agent lives **outside the repo** at
`$LEGAL_TRANSLATION_PRIVATE_DIR`. The repo tree only contains code, docs,
and scaffolding.

## One-time setup

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"/{input,output/documents,output/working,library,glossary,_private}
```

Add the `export` line to `~/.zshrc` or `~/.bashrc` so it persists.

## Layout

```text
$LEGAL_TRANSLATION_PRIVATE_DIR/
├── input/          ← Source documents
├── output/
│   ├── documents/  ← Final translated documents
│   └── working/    ← Intermediate artifacts (checkpoint.json, pass-a.md, ...)
├── library/        ← User-managed references, glossaries, style guides
├── glossary/       ← Persistent glossary store
└── _private/       ← Internal work product (design doc, notes)
```

## Why not keep it in the repo?

Source legal documents and house glossaries are confidential. Keeping
them outside the repo tree eliminates the possibility of an accidental
`git add --force` or a mis-scoped branch push leaking them.

## Migrating Existing Repo-Root Data

Run a dry-run first:

```bash
python3 .claude/scripts/migrate-private-data.py --dry-run
```

The helper writes a migration manifest under
`$LEGAL_TRANSLATION_PRIVATE_DIR/_private/migration-manifests/`. When you run
with `--apply`, it records both source and target inventories with sha256
checksums. Public repo scaffolding under `library/_example` is never moved.
