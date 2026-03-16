# back-translation-checker Skill

Select critical segments for back-translation, dispatch translator sub-agent, compare semantics, and classify divergences. Hard mode only (Step 8).

## Capabilities

1. **Critical Segment Selection** (LLM judgment)
   - Select 30–50% of document volume for back-translation
   - Selection criteria (highest legal weight):
     - Definitions article (정의 조항)
     - Rights and obligations clauses (권리·의무 조항)
     - Liability limitations (책임 제한)
     - Warranty disclaimers (보증 부인)
     - Termination provisions (해지/해제 조항)
     - Clauses where Pass A and Pass B had significant divergence (from synthesis-log.json)
   - Output: list of selected article/section IDs with selection rationale

2. **Back-Translation Dispatch**
   - Send selected translated segments to `translator` sub-agent for reverse translation
   - Target → Source language (e.g., KO → EN)
   - Back-translation uses fresh context, no access to original source

3. **Semantic Comparison** (LLM judgment)
   - Compare back-translated text against original source text
   - Focus on: legal meaning shifts, obligation scope changes, ambiguity introduction, rights alteration

4. **Divergence Classification**

   | Severity | Definition | Action |
   |----------|-----------|--------|
   | **Critical** | Legal meaning altered — rights, obligations, or liability shifted | Mandatory correction before proceeding |
   | **Major** | Ambiguity introduced — reasonable readers could interpret differently | Flag + recommend correction |
   | **Minor** | Stylistic difference — meaning preserved but phrasing differs | Log only |

5. **Remediation Dispatch**
   - Critical divergences → return to synthesis-editor with clause + back-translation evidence
   - Maximum 2 correction rounds
   - Critical persists → escalate to user with side-by-side comparison

## Workflow

```
synthesized-verified.md + synthesis-log.json + source-parsed.md
    │
    ├── Select critical segments (30-50%)
    │
    ├── Dispatch translator sub-agent (reverse direction)
    │       ↓
    │   back-translation segments
    │
    ├── Semantic comparison vs original source
    │       ↓
    │   Divergence classification (Critical/Major/Minor)
    │
    └── back-translation-report.json
            │
            ├── Zero Critical → proceed to Step 9
            └── Critical found → remediation loop
```

## When to Use

- **WF1 Step 8**: Back-Translation Verification (Hard mode ONLY)

## Output Schema

```json
{
  "segments_selected": 8,
  "segments_total": 14,
  "selection_rationale": ["definitions", "liability", "warranty", "synthesis_divergence"],
  "findings": [
    {
      "article": "Article 7.3",
      "original": "...",
      "translation": "...",
      "back_translation": "...",
      "divergence_type": "major",
      "description": "...",
      "action": "corrected",
      "corrected_translation": "..."
    }
  ],
  "critical_count": 0,
  "major_count": 2,
  "minor_count": 5
}
```

## Checkpoint

Step 8 completion:
- `step_8.status` → `"completed"`
- `step_8.outputs` → `["back-translation-report.json"]`
- `step_8.remediation_rounds` → count
- `last_completed_step` → `8`
