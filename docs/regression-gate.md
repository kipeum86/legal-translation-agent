# Local Regression Gate

Run the full local release gate before release-oriented changes:

```bash
python3 .claude/scripts/check.py
```

This is the same entry point used by CI. It runs:

- dry-run regression
- pytest suites for shared scripts and implemented skills
- Python syntax compilation for release scripts
- shell syntax checks for parser/converter scripts

The dry-run regression creates a temporary `${LEGAL_TRANSLATION_PRIVATE_DIR}` and verifies:

- checkpoint and manifest schema creation
- Fast, Normal, and Hard mode execution contracts in `manifest.mode_plan`
- structural verification PASS on the fixture pair
- term candidate extraction and glossary usage
- context pack token reduction report
- Library top-K retrieval
- batch dry-run plan and `batch-glossary-review.json` lock queue
- DOCX table, footnote, header, and tracked-change sidecar extraction
- PDF low-density OCR warning
- final output provenance and manifest freshness

Use `python3 .claude/scripts/run-regression.py --keep-private-dir` when you need to inspect generated artifacts from the regression fixture.
