# library-comparator Skill

Compare current translation against Library reference translations, custom glossaries, and style guides for house-preference alignment. Hard mode only (Step 9).

## Skip Condition

**If no Library assets exist for the current target language pair, skip this step entirely** with log message:
> "No Library reference available for {src}→{tgt}. Step 9 skipped."

A Library profile being active is not sufficient — there must be at least one reference translation OR style guide for this specific language pair.

## Capabilities

1. **Reference Translation Comparison** (LLM judgment)
   - Align comparable sections between current translation and gold-standard reference
   - Identify divergences in terminology, phrasing, structure, register
   - NOT about copying the reference — about catching contradictions to established house preferences

2. **Style Guide Compliance Check** (LLM judgment)
   - Verify translation follows Library style guide conventions for target language
   - Check: register, tone, prohibited expressions, preferred phrasings, formatting

3. **Library Glossary Final Consistency Check**
   - Cross-check all terms in final translation against Library custom glossary
   - Flag any remaining mismatches after synthesis

4. **Comparison Report Generation**

   | Category | Example | Action |
   |----------|---------|--------|
   | **Term mismatch** | Library uses "이용자" but translation uses "사용자" | Correct to Library term |
   | **Register deviation** | Library requires ~합니다 체 but translation uses ~한다 체 | Correct to Library register |
   | **Phrasing preference** | Reference uses "본 약관" but translation uses "이 약관" | Flag for user decision (not auto-correct) |
   | **Structural convention** | Reference uses ①②③ but translation uses 1.2.3 | Correct to Library convention |

   - Term mismatches and register deviations: auto-correct
   - Phrasing preferences: flag only (user decides)

## Workflow

```
Translation (post-Step 8) + Library assets
    │
    ├── Reference translation comparison (if gold-standard exists)
    ├── Style guide compliance check
    ├── Library glossary final consistency
    │       ↓
    └── library-comparison-report.json
            │
            ├── All corrections applied → proceed to Step 10
            └── Auto-retry ×1 → escalate to user
```

## When to Use

- **WF1 Step 9**: Library Reference Comparison (Hard mode ONLY, with Library assets)

## Failure Handling

- Auto-retry ×1 on failure → escalate to user
- Missing Library files → skip with log (not an error)

## Checkpoint

Step 9 completion:
- `step_9.status` → `"completed"` or `"skipped"`
- `step_9.outputs` → `["library-comparison-report.json"]` or `[]`
- `step_9.skip_reason` → reason if skipped
- `last_completed_step` → `9`
