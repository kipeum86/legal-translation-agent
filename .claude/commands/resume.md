Path note: Any `input/`, `output/`, `library/`, `glossary/`, or `_private/`
path below means the matching directory inside `${LEGAL_TRANSLATION_PRIVATE_DIR}`.

Resume an interrupted translation job.

1. Check for `output/working/checkpoint.json`
2. If checkpoint exists:
   - Display last completed step, source/target language, mode, and Library profile
   - Ask: "이전 작업을 이어서 진행할까요? (Y/N)"
   - If Y: verify all referenced artifacts exist, then re-enter pipeline at the next step
   - If N: ask whether to archive or discard working artifacts
3. If no checkpoint exists:
   - Inform: "진행 중인 작업이 없습니다. /translate 로 새 번역을 시작하세요."
