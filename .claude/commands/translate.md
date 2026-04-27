Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Translate the document(s) in the input folder.

Execute WF1 — Document Translation Pipeline:

1. Scan `input/` folder for source documents (.docx, .pdf, .md, .txt)
2. If $ARGUMENTS provided, parse for: target language, mode (fast/normal/hard), Library profile
3. If no target language specified, ask: "대상 언어는? (en / ko / zh-cn / zh-tw / ja)"
4. If mode not specified, default to Normal. Confirm: "모드: Normal (기본) — 초안은 fast, 고위험 문서는 hard를 지정하세요."
5. If first job of session, ask output format: "출력 형식은? (채팅 / TXT / Markdown / DOCX — 기본값: DOCX)"
6. Execute Steps 1–5 for Fast, Steps 1–7 for Normal, or Steps 1–10 for Hard:
   - Step 1: Document Ingestion & Analysis (document-analyzer skill)
     - Parser must create `source-structure.json`; validate it before translation.
   - Step 2: Terminology Extraction & Glossary Setup (terminology-manager skill)
   - Step 3: Translation Pass A (translator sub-agent)
   - Step 4: Translation Pass B (translator sub-agent — fresh context; skipped in Fast)
   - Step 5: Comparative Synthesis (synthesis-editor sub-agent; skipped in Fast)
   - Step 6: Structural Verification (structural-verifier skill)
   - Step 7: Output Assembly & Quality Gate (quality-checker + output-generator skills)
   - Step 8: Back-Translation Verification (Hard only — back-translation-checker skill)
   - Step 9: Library Reference Comparison (Hard only — library-comparator skill with top-K retrieval)
   - Step 10: Editorial Polish & Final Quality Gate (Hard only — editorial-reviewer sub-agent)
7. Save output to `output/documents/` and working artifacts to `output/working/` under `${LEGAL_TRANSLATION_PRIVATE_DIR}`
8. Merge working glossary into persistent glossary

Implementation note: use `.claude/scripts/translate-job.py start --dry-run ...`
to create and validate job checkpoint/manifest state before executing the
pipeline manually. Record produced sidecars with `translate-job.py record-artifact`
and blocking quality failures with `translate-job.py record-failure` so resume
can verify artifact checksums and retry state.

Use `translate-job.py validate-gate` for schema plus semantic gates, for example
`--expect overall_status=PASS`. Rollout policy defaults to `warn`; set
`--validation-policy enforce-new-jobs` on new jobs when moving to blocking gates.

Use `.claude/scripts/build-context-pack.py` before dispatching segment-level
translator/synthesis work, then measure before/after prompt payloads with
`.claude/scripts/estimate-context-cost.py`.

For file outputs, call `file-converter.sh` with `--job-id <job_id>` so the final
document and `<final>.provenance.json` are recorded in the manifest.
