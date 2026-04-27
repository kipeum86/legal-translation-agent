# Release Notes — v1.2.0

> A safer, clearer, and more dependable legal translation workflow.
> 더 안전하고, 더 명확하고, 더 안정적인 법률 번역 워크플로우입니다.

---

## English

### What Changed

#### 1. Your documents are better separated from the code

Source documents, translation outputs, glossaries, Library assets, and local notes now live in a private folder outside the repository. This makes it much harder to accidentally include client documents or working files when sharing or pushing the project.

#### 2. The agent is more careful with untrusted document text

Legal documents and reference files can contain text that looks like instructions to an AI system. The agent now treats document content as material to translate or compare, not as instructions to follow. Suspicious role markers and prompt-injection style phrases are isolated during ingestion.

#### 3. Translation completeness checks are stronger

The agent now checks more than simple article counts. It is better at detecting missing or shifted sections, list items, footnotes, and glossary usage problems before a translation is treated as ready.

#### 4. Translation modes are clearer

- **Fast**: quick internal draft only
- **Normal**: default dual-pass workflow for standard legal translation
- **Hard**: extra verification for high-stakes or external-facing documents

Fast mode is clearly marked as draft-only. Normal mode keeps the dual-pass quality baseline.

#### 5. Glossary consistency is improved

Defined terms are detected more consistently, glossary usage is checked before delivery, and batch translation now creates a review queue for shared defined terms and party names.

#### 6. Batch translation is easier to control

For multiple related documents, the agent now creates a batch plan first. Shared terms and party names can be reviewed before translation starts, which helps keep a set of agreements consistent.

#### 7. DOCX and PDF handling is more reliable

DOCX parsing now preserves more legal-document details, including tables, footnotes, headers/footers, comments, and tracked changes. PDF parsing can warn when extracted text is too sparse and may need OCR review.

#### 8. Library references are used more selectively

When using Library references, the agent now focuses on the most relevant reference material instead of loading everything. This improves focus and helps reduce unnecessary context.

#### 9. Local verification is simpler

There is now one release check command:

```bash
python3 .claude/scripts/check.py
```

It runs the local regression fixture, unit tests, and syntax checks used by CI.

### Recommended Upgrade Steps

1. Pull the latest version.
2. Set `LEGAL_TRANSLATION_PRIVATE_DIR` if you have not already done so.
3. Put source documents in `${LEGAL_TRANSLATION_PRIVATE_DIR}/input/`.
4. Run `python3 .claude/scripts/check.py` once after updating.
5. Continue using `/translate`, `/translate-batch`, `/glossary`, and `/library` as usual.

### Reminder

This is machine-assisted legal translation. A qualified professional should review every output before reliance, filing, publication, or client delivery.

---

## 한국어

### 무엇이 좋아졌나요?

#### 1. 문서와 코드가 더 안전하게 분리됩니다

원문 문서, 번역 결과물, 용어집, Library 자산, 로컬 노트가 이제 리포지토리 바깥의 private 폴더에 저장됩니다. 프로젝트를 공유하거나 GitHub에 올릴 때 고객 문서나 작업 파일이 실수로 포함될 가능성을 줄입니다.

#### 2. 원문 문서 안의 수상한 지시문에 더 안전합니다

문서나 참조 파일 안에는 AI에게 명령처럼 보이는 문구가 들어 있을 수 있습니다. 이제 에이전트는 그런 내용을 지시가 아니라 번역·비교 대상 데이터로 취급합니다. 역할 표식이나 prompt-injection 형태의 문구는 인제스트 단계에서 격리됩니다.

#### 3. 누락 검사가 더 강해졌습니다

단순히 조문 개수만 보는 수준을 넘어, 빠진 조항, 순서가 밀린 항목, 목록, 각주, 용어집 사용 문제를 더 잘 잡아냅니다. 번역물이 준비됐다고 보기 전에 더 많은 구조적 오류를 확인합니다.

#### 4. 번역 모드가 더 명확해졌습니다

- **Fast**: 내부 검토용 빠른 초안
- **Normal**: 일반 법률 번역 기본 모드
- **Hard**: 외부 제출·고위험 문서를 위한 추가 검증 모드

Fast 결과물은 초안용으로 명확히 표시됩니다. Normal 모드는 기존 이중 패스 품질 기준을 유지합니다.

#### 5. 용어 일관성이 좋아졌습니다

정의 용어를 더 안정적으로 찾아내고, 결과물에 용어집이 제대로 반영됐는지 확인합니다. 배치 번역에서는 여러 문서에 함께 등장하는 정의 용어와 당사자명을 먼저 검토할 수 있습니다.

#### 6. 배치 번역을 더 통제하기 쉬워졌습니다

관련 문서 여러 개를 번역할 때 먼저 배치 계획을 만듭니다. 번역을 시작하기 전에 공통 용어와 당사자명을 검토할 수 있어, 계약서 세트 전체의 표현을 맞추기 쉬워졌습니다.

#### 7. DOCX와 PDF 처리 안정성이 좋아졌습니다

DOCX 문서의 표, 각주, 머리말/꼬리말, 주석, 변경 추적 정보를 더 잘 보존합니다. PDF는 추출된 텍스트가 너무 적으면 OCR 검토가 필요할 수 있음을 경고합니다.

#### 8. Library 참조를 더 선별적으로 사용합니다

Library 참조를 사용할 때 전체 자료를 무작정 넣지 않고, 현재 문서와 관련성이 높은 참조를 중심으로 사용합니다. 번역 흐름이 더 집중되고 불필요한 컨텍스트 사용을 줄입니다.

#### 9. 로컬 검증이 쉬워졌습니다

업데이트 후 아래 명령 하나로 기본 상태를 확인할 수 있습니다:

```bash
python3 .claude/scripts/check.py
```

로컬 회귀 fixture, 단위 테스트, 문법 검사를 한 번에 실행합니다.

### 권장 업데이트 순서

1. 최신 버전을 받습니다.
2. 아직 설정하지 않았다면 `LEGAL_TRANSLATION_PRIVATE_DIR`를 설정합니다.
3. 원문 문서는 `${LEGAL_TRANSLATION_PRIVATE_DIR}/input/`에 둡니다.
4. 업데이트 후 `python3 .claude/scripts/check.py`를 한 번 실행합니다.
5. 이후 `/translate`, `/translate-batch`, `/glossary`, `/library`를 평소처럼 사용합니다.

### 다시 한 번 안내

이 도구는 기계 보조 법률 번역 도구입니다. 제출, 공개, 고객 전달, 또는 법적 의존 전에는 반드시 자격 있는 전문가가 결과물을 검토해야 합니다.
