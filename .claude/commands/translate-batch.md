Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Translate multiple documents in the input folder as a batch.

Execute WF4 — Batch Translation Pipeline:

1. Scan `input/` folder for all source documents
2. List detected files and confirm batch parameters with user:
   - Target language
   - Mode (Normal/Hard)
   - Library profile (optional)
   - Processing order
3. If $ARGUMENTS provided, parse for batch parameters
4. Execute WF1 for each document sequentially:
   - Document 1: full WF1 pipeline, establishing working glossary
   - Documents 2–N: WF1 with cumulative working glossary (new terms appended, existing locked)
5. After all documents complete: cross-document consistency check
   - Identical translation of party names across documents
   - Identical translation of defined terms appearing in multiple documents
   - Consistent date format conventions
   - Consistent legal reference phrasing
6. Merge cumulative glossary into persistent glossary store
7. Present batch summary to user
