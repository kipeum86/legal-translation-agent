Run or re-run the onboarding interview to configure agent settings.

1. If `config.json` exists, show current settings and ask: "현재 설정을 수정하시겠어요? (전체 재설정 / 항목별 수정 / 취소)"
2. If `config.json` does not exist, run the full onboarding interview per the Onboarding Protocol in CLAUDE.md
3. Walk through each question group one at a time (never dump all questions at once)
4. On completion, save to `config.json` in the project root
5. If $ARGUMENTS contains "reset", skip the existing settings check and run full interview from scratch
