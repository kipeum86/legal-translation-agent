Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Translate multiple documents in the input folder as a batch.

Execute WF4 — Batch Translation Pipeline:

1. Scan `input/` folder for all source documents
2. List detected files and confirm batch parameters with user:
   - Target language
   - Mode (Fast/Normal/Hard)
   - Library profile (optional)
   - Processing order
3. If $ARGUMENTS provided, parse for batch parameters
4. Prefer `.claude/scripts/translate-batch.py start --dry-run --input input/ --target <lang>`
   to create the batch plan and glossary review queue.
5. Review `output/working/batches/<batch-id>/batch-glossary-review.json` before translation:
   - `locks.defined_terms` and `locks.party_names` are batch-level lock candidates
   - `conflicts[]` requires user decision; do not auto-resolve conflicts
   - Phase 3 is blocked until the review queue is approved
6. Execute batch in three phases:
   - Phase 1: parse, structure count, and term candidate extraction for all documents in parallel
   - Phase 2: resolve/approve `batch-glossary-review.json`
   - Phase 3: translate documents in parallel with batch-level locked terms
7. After all documents complete: cross-document consistency check
   - Identical translation of party names across documents
   - Identical translation of defined terms appearing in multiple documents
   - Consistent date format conventions
   - Consistent legal reference phrasing
8. Merge cumulative glossary into persistent glossary store
9. Present batch summary to user
