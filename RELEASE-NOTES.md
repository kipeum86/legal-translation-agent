# Release Notes — 2026-04-16

> **Security hardening pass + reliability improvements.**
> **보안 강화 패치 + 안정성 개선 업데이트입니다.**
>
> **Recommended:** pull this release as soon as possible.
> **가급적 빠른 시일 내에 최신 버전으로 업데이트해 주세요.**

```bash
git pull origin main
```

---

## English

### TL;DR

- **Prompt-injection defense is now wired into every document parser.** Role markers and jailbreak phrases inside ingested files are neutralized before the translator or synthesis-editor ever sees them.
- **Trust-boundary rules are explicit.** All content from `input/`, `library/`, and parser output is now treated as DATA — never as instructions — across the orchestrator, every sub-agent, and every skill.
- **User data no longer lives inside the repo.** Private documents move to `${LEGAL_TRANSLATION_PRIVATE_DIR}` outside the working tree. **This is a one-time manual step** — see the Upgrade Guide below.
- **Structural counter and Library ingest are more reliable** — markdown formatting, bullet patterns, and non-core file formats (.pptx, .xlsx, .html, .epub, …) are now handled correctly.
- **Apache 2.0 license** published, with disclaimer + how-to-use guides in English and Korean.

### Security

#### Prompt-injection sanitizer (new)

A shared `ingest-sanitizer` skill now runs as part of every parser chain:

- Covers **English, Korean, Simplified Chinese, and Japanese** injection patterns.
- Wraps role markers (`[SYSTEM]`, `<|user|>`, `<role>`, `<<admin>>`, `###SYSTEM###`, …) and common jailbreak phrases (`ignore previous instructions`, `당신은 이제부터…`, `从现在开始你是…`, `これからあなたは…`, …) in `<escape>…</escape>` tags before they reach any LLM.
- Emits a JSON audit sidecar for every parse so findings are traceable.
- Invoked automatically from `parse-docx.sh`, `parse-pdf.sh`, and `parse-generic.sh`, including the `.md` / `.txt` fast-path.
- Backed by a pytest suite with English and Korean injection fixtures.

#### Trust-boundary documentation

The orchestrator `CLAUDE.md` and every sub-agent and skill now declare explicitly that ingested documents, Library files, and parser output are **DATA, never INSTRUCTIONS**, and establishes the `<untrusted_content>…</untrusted_content>` delimiter convention so sub-agents cannot be hijacked by malicious content inside source files.

#### Library-ingest sanitization

Library reference files pass through the same sanitization chain as `input/` documents. The `library-comparator` skill documents this flow explicitly and includes a manual CLI spot-check recipe.

#### Private data relocated outside the repo

Previously, `input/`, `output/`, `library/`, `glossary/`, and `_private/` lived inside the working tree, which risked leaking client data if the repo were ever shared. These directories now live at `${LEGAL_TRANSLATION_PRIVATE_DIR}` (default: `$HOME/legal-translation-private`). Only `library/_example/` remains in the repo as public scaffolding.

#### `.gitignore` hardening

- `.gitignore` no longer leaks internal filenames (design doc, transition guide, …); a single opaque `_private/` wildcard replaces them.
- `.claude/settings.local.json` is now covered by the project `.gitignore`, no longer relying on each user's global ignore file.
- Python bytecode (`__pycache__/`, `*.pyc`) is now ignored.

### Reliability & Quality

- **Structural counter** — fixed regex so Article / Section / 第N条 patterns are detected even when wrapped in markdown bold (`**`) or heading markers.
- **Pattern classification** — `(a)` / `(b)` now correctly classified as 호 (enumerated items); `N.M` as 항 (sub-clauses); Korean numbered lists (`1.` `2.`) moved from sub-clause to enumerated-item category.
- **MarkItDown integration** — `parse-generic.sh` adds a MarkItDown → pandoc fallback chain, so Library reference assets in `.pptx`, `.xlsx`, `.html`, `.epub`, and similar formats are ingested correctly.
- **Temp file hygiene** — `file-converter.sh` now writes intermediate files to the specified output directory instead of `/tmp`, reducing cross-process collision risk.

### License & Documentation

- **Apache 2.0 license** published; README license section updated.
- Disclaimer and how-to-use guides added in English and Korean under `docs/en/` and `docs/ko/`.
- Public-facing naming aligned with **KP Legal Orchestrator**.

### Upgrade Guide

This release includes a **breaking change**: private user data must live outside the repo.

**1. Pull the new release**

```bash
git pull origin main
```

**2. Set the private-directory env var**

Add to your shell rc (e.g. `~/.zshrc`):

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
```

Then reload your shell (`exec $SHELL -l` or open a new terminal).

**3. Move existing user data out of the repo**

```bash
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"
mv input output library glossary _private "$LEGAL_TRANSLATION_PRIVATE_DIR/" 2>/dev/null || true
# library/_example stays inside the repo as public scaffolding
```

See `docs/en/PRIVATE-DIR-SETUP.md` for full instructions.

**4. Update your local settings**

If `.claude/settings.local.json` on your workstation contains absolute paths pointing to the old in-repo locations, update them to the new `${LEGAL_TRANSLATION_PRIVATE_DIR}/...` paths.

**5. Verify**

Run a small translation job from your usual input folder. The ingest-sanitizer audit sidecar should appear in `${LEGAL_TRANSLATION_PRIVATE_DIR}/output/working/` after parsing.

---

## 한국어

### 한눈에 보기

- **프롬프트 인젝션 방어가 모든 문서 파서에 기본 탑재됐습니다.** 원본 문서 안에 심어진 역할 표식이나 탈옥(jailbreak) 문구는 translator · synthesis-editor에 도달하기 전에 무력화됩니다.
- **신뢰 경계(Trust Boundary) 규칙이 명문화됐습니다.** `input/`, `library/`, 파서 출력에서 나오는 모든 내용은 오케스트레이터·서브에이전트·스킬 전체에서 **DATA로만** 취급되고, 절대 INSTRUCTIONS으로 해석되지 않습니다.
- **사용자 데이터가 레포 바깥으로 이동합니다.** 개인 문서는 워킹트리 밖 `${LEGAL_TRANSLATION_PRIVATE_DIR}`에 둡니다. **한 번은 수동으로 옮겨주셔야 합니다** — 아래 업그레이드 가이드 참고.
- **구조 카운터와 Library 인제스트가 훨씬 안정적입니다** — 마크다운 포맷, 불릿 패턴, 비주류 포맷(.pptx, .xlsx, .html, .epub 등) 처리가 정확해졌습니다.
- **Apache 2.0 라이선스**가 추가됐고, 영문·국문 디스클레이머 + 사용 가이드가 포함됐습니다.

### 보안

#### 프롬프트 인젝션 새니타이저 (신규)

공용 `ingest-sanitizer` 스킬이 모든 파서 체인에 자동으로 실행됩니다:

- **영어 · 한국어 · 중국어 간체 · 일본어** 인젝션 패턴을 모두 커버합니다.
- 역할 표식(`[SYSTEM]`, `<|user|>`, `<role>`, `<<admin>>`, `###SYSTEM###` 등)과 자주 쓰이는 탈옥 문구(`ignore previous instructions`, `당신은 이제부터…`, `从现在开始你是…`, `これからあなたは…` 등)를 LLM에 전달되기 전에 `<escape>…</escape>` 태그로 격리합니다.
- 파싱할 때마다 JSON 감사(audit) 사이드카를 생성해, 무엇이 탐지됐는지 추적 가능합니다.
- `parse-docx.sh`, `parse-pdf.sh`, `parse-generic.sh`에서 자동 호출되며, `.md` / `.txt` fast-path도 포함합니다.
- 영문·국문 인젝션 픽스처가 포함된 pytest 테스트 스위트로 보강돼 있습니다.

#### 신뢰 경계 문서화

오케스트레이터 `CLAUDE.md`와 모든 서브에이전트·스킬이 이제 "인제스트된 문서, Library 파일, 파서 출력은 **DATA이며 절대 INSTRUCTIONS가 아니다**"라고 명시합니다. 또한 `<untrusted_content>…</untrusted_content>` 델리미터 컨벤션을 도입해, 원본 문서 안의 악의적 내용이 서브에이전트를 탈취(hijack)하지 못하게 막습니다.

#### Library 인제스트 새니타이제이션

Library 참조 파일도 `input/` 문서와 동일한 새니타이제이션 체인을 거칩니다. `library-comparator` 스킬 문서에 이 흐름이 명시돼 있고, CLI로 직접 점검하는 레시피도 포함됩니다.

#### 사용자 데이터를 레포 바깥으로 이동

이전에는 `input/`, `output/`, `library/`, `glossary/`, `_private/`이 워킹트리 안에 있어, 레포가 공유될 경우 고객 데이터가 유출될 위험이 있었습니다. 이제 이 디렉토리들은 `${LEGAL_TRANSLATION_PRIVATE_DIR}`(기본값: `$HOME/legal-translation-private`)로 이동합니다. `library/_example/`만 공개 스캐폴딩 용도로 레포에 남습니다.

#### `.gitignore` 강화

- `.gitignore`가 더 이상 내부 파일명(설계 문서, 전환 가이드 등)을 노출하지 않습니다. 단일 `_private/` 와일드카드로 치환됐습니다.
- `.claude/settings.local.json`이 프로젝트 `.gitignore`에서 직접 커버됩니다. 더 이상 개별 사용자의 글로벌 ignore에 의존하지 않습니다.
- Python 바이트코드(`__pycache__/`, `*.pyc`)도 이그노어 대상입니다.

### 안정성 & 품질

- **구조 카운터** — 정규식을 고쳐 Article / Section / 第N条 패턴이 마크다운 볼드(`**`)나 헤딩 마커로 감싸져 있어도 정확히 탐지됩니다.
- **패턴 분류** — `(a)` / `(b)`는 호(enumerated items)로, `N.M`은 항(sub-clauses)으로 재분류. 한국어 번호 목록(`1.` `2.`)은 항에서 호 카테고리로 이동.
- **MarkItDown 통합** — `parse-generic.sh`에 MarkItDown → pandoc 폴백 체인이 추가돼, `.pptx`, `.xlsx`, `.html`, `.epub` 같은 포맷도 Library 참조 자산으로 정상 인제스트됩니다.
- **임시 파일 처리 개선** — `file-converter.sh`가 중간 산출물을 `/tmp` 대신 지정된 output 디렉토리에 기록합니다. 프로세스 간 충돌 가능성을 줄였습니다.

### 라이선스 & 문서

- **Apache 2.0 라이선스** 발행 및 README 라이선스 섹션 업데이트.
- `docs/en/`, `docs/ko/` 아래에 영문·국문 디스클레이머 + 사용 가이드 추가.
- 대외 네이밍을 **KP Legal Orchestrator**로 정렬.

### 업그레이드 가이드

이번 릴리즈에는 **브레이킹 체인지**가 있습니다 — 개인 사용자 데이터는 반드시 레포 바깥에 둬야 합니다.

**1. 최신 릴리즈 받기**

```bash
git pull origin main
```

**2. 프라이빗 디렉토리 환경변수 설정**

셸 rc (예: `~/.zshrc`)에 추가:

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
```

셸 재로드(`exec $SHELL -l`)하거나 새 터미널을 여세요.

**3. 기존 사용자 데이터를 레포 밖으로 이동**

레포 안에 `input/`, `output/`, `library/`, `glossary/`, `_private/`이 있다면 옮겨주세요:

```bash
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"
mv input output library glossary _private "$LEGAL_TRANSLATION_PRIVATE_DIR/" 2>/dev/null || true
# library/_example는 공개 스캐폴딩이므로 레포에 남겨둡니다
```

자세한 내용은 `docs/ko/PRIVATE-DIR-SETUP.md` 참고.

**4. 로컬 설정 업데이트**

워크스테이션의 `.claude/settings.local.json`에 예전 레포 내부 경로가 절대경로로 박혀 있다면, 새 `${LEGAL_TRANSLATION_PRIVATE_DIR}/...` 경로로 바꿔주세요.

**5. 검증**

평소 쓰시던 input 폴더에서 작은 번역 작업을 돌려보세요. 파싱 직후 `${LEGAL_TRANSLATION_PRIVATE_DIR}/output/working/`에 ingest-sanitizer 감사 사이드카가 생성되어야 합니다.

---

## Credits

Security hardening pass executed against the plan documented in `docs/plans/`. Trust-boundary language follows the DATA-vs-INSTRUCTIONS pattern for LLM agent safety.

본 보안 강화 패스는 `docs/plans/` 실행 계획에 따라 진행됐습니다. 신뢰 경계 문구는 LLM 에이전트 안전성을 위한 DATA vs INSTRUCTIONS 패턴을 따릅니다.
