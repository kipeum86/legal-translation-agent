# quality-checker Skill

Execute quality gate checklists before final delivery. 6-item gate for Normal mode, 10-item gate for Hard mode.

## Normal Mode — 6-Item Quality Gate (Step 7)

| # | Item | Verification Method |
|---|------|-------------------|
| 1 | **Completeness** — structural verification all PASS | Check verification-checklist.json: overall_status = PASS |
| 2 | **Term consistency** — every glossary term identical throughout | Scan translation for each working glossary term; flag deviations |
| 3 | **Register uniformity** — no informal language, register shifts, translationese | LLM read-through: check for 반말/존댓말 mixing, 번역투, inconsistent formality |
| 4 | **Formatting preservation** — bold, ALL CAPS, numbering, indentation match source | Compare source formatting cues against translation |
| 5 | **Proper noun integrity** — brand names, URLs, platform names unchanged | Scan for known proper nouns from source; verify not translated/transliterated |
| 6 | **No fabrication** — no content added beyond source; uncertain flagged with `[TN]` | LLM check: no hallucinated clauses, no added legal provisions |

## Hard Mode — 10-Item Quality Gate (Step 10)

Extends Normal gate with 4 additional items:

| # | Item | Source |
|---|------|--------|
| 7 | **Back-translation clearance** — zero Critical divergences; all Major resolved | Check back-translation-report.json: critical_count = 0 |
| 8 | **Library alignment** — term mismatches and register deviations corrected | Check library-comparison-report.json: all auto-corrections applied |
| 9 | **Native fluency** — reads as original-language document, not as translation | LLM monolingual read-through in target language |
| 10 | **Editorial consistency** — no stylistic seams between corrected and uncorrected sections | LLM check for voice/style uniformity across the full document |

## Workflow

```
Translation + all artifacts
    │
    ├── Check items 1-6 (both modes)
    │   ├── All PASS → proceed
    │   └── Any FAIL → auto-remediate ×1
    │
    ├── [Hard mode only] Check items 7-10
    │   ├── All PASS → proceed
    │   └── Any FAIL → auto-remediate ×1
    │
    └── Quality gate result
            ├── ALL PASS → deliver
            └── FAIL after remediation → deliver with flags
```

## When to Use

- **WF1 Step 7**: 6-item gate (Normal mode exit)
- **WF1 Step 10**: 10-item gate (Hard mode exit)

## Remediation Protocol

1. On gate failure: identify specific failing items with details
2. Auto-remediate x1:
   - Item 2 (term consistency) → find and fix deviations
   - Item 3 (register) → fix register shifts
   - Item 4 (formatting) → restore formatting
   - Item 5 (proper nouns) → restore originals
   - Items 7-10 → targeted corrections
3. Re-run quality gate after remediation
4. Second failure → deliver with flags:
   > "Quality gate items {N} did not pass after remediation. Flagged for manual review."

## Output

Quality gate results included in the final output document as an appendix:

```
## Quality Gate Results
| # | Item | Status |
|---|------|--------|
| 1 | Completeness | PASS |
| 2 | Term consistency | PASS |
| ... | ... | ... |
```
