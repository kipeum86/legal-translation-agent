Translate the document(s) in the input folder.

Execute WF1 — Document Translation Pipeline:

1. Scan `input/` folder for source documents (.docx, .pdf, .md, .txt)
2. If $ARGUMENTS provided, parse for: target language, mode (normal/hard), Library profile
3. If no target language specified, ask: "대상 언어는? (en / ko / zh-cn / zh-tw / ja)"
4. If mode not specified, default to Normal. Confirm: "모드: Normal (기본) — Hard 모드 필요 시 'hard'를 지정하세요."
5. If first job of session, ask output format: "출력 형식은? (채팅 / TXT / Markdown / DOCX — 기본값: DOCX)"
6. Execute Steps 1–7 (Normal) or Steps 1–10 (Hard):
   - Step 1: Document Ingestion & Analysis (document-analyzer skill)
   - Step 2: Terminology Extraction & Glossary Setup (terminology-manager skill)
   - Step 3: Translation Pass A (translator sub-agent)
   - Step 4: Translation Pass B (translator sub-agent — fresh context)
   - Step 5: Comparative Synthesis (synthesis-editor sub-agent)
   - Step 6: Structural Verification (structural-verifier skill)
   - Step 7: Output Assembly & Quality Gate (quality-checker + output-generator skills)
   - Step 8: Back-Translation Verification (Hard only — back-translation-checker skill)
   - Step 9: Library Reference Comparison (Hard only — library-comparator skill)
   - Step 10: Editorial Polish & Final Quality Gate (Hard only — editorial-reviewer sub-agent)
7. Save output to `output/documents/` and working artifacts to `output/working/`
8. Merge working glossary into persistent glossary
