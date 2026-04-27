# structural-verifier Skill

Deterministic comparison of source and target document structures to guarantee zero-omission.

## Capabilities

1. **Target Structure Counting** (`../document-analyzer/scripts/structural-counter.py`)
   - Run the same counter on the translated document to produce target structural inventory
   - Usage: `python3 structural-counter.py <synthesized.md> <target_lang> <target-inventory.json>`

2. **Count Comparison** (`scripts/count-comparator.py`)
   - Canonical article-ID comparison: missing, extra, and reordered articles
   - Article-level comparison: sub-clauses, enumerated items
   - Document-level blocking comparison: total articles, total sub-clauses, total enumerated items, defined term count, footnotes
   - Usage: `python3 scripts/count-comparator.py <source-inventory.json> <target-inventory.json> <output_path>`
   - Outputs: `verification-checklist.json` with `blocking_failures` and per-article PASS/FAIL status

3. **LLM Spot-Check** (LLM judgment)
   - For any FAIL articles, perform targeted review of the specific gap
   - Determine if the mismatch is a real omission or a counting artifact

## Workflow

```
synthesized.md + source structural-inventory.json
    │
    ├── structural-counter.py (on target)
    │       ↓
    │   target-structural-inventory.json
    │
    └── count-comparator.py
            ↓
        verification-checklist.json
            │
            ├── All PASS → proceed to Step 7
            └── Any FAIL → remediation
```

## When to Use

- **WF1 Step 6**: Structural Verification (both Normal and Hard modes)

## Remediation Protocol

1. On FAIL: identify specific missing/extra articles or sub-clauses
2. Return to synthesis-editor sub-agent with targeted gap instruction:
   - "Article X is missing sub-clause Y. Source text: [excerpt]. Add the missing sub-clause."
3. Re-run structural verification after remediation
4. Maximum 2 remediation rounds
5. Still failing after 2 rounds → flag `[STRUCTURAL GAP: {detail}]` inline in the translation + escalate to user

## Failure Handling

- Counter script failure → fall back to LLM-based manual count
- Persistent count mismatch → escalate with side-by-side comparison for user review
- Structural omissions are ALWAYS Critical — never skip-and-log

## Checkpoint

Step 6 completion:
- `step_6.status` → `"completed"`
- `step_6.outputs` → `["verification-checklist.json"]`
- `step_6.remediation_rounds` → count of remediation attempts
- `last_completed_step` → `6`
