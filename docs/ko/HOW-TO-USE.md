# 법률 번역 에이전트 사용 가이드

[English](../en/HOW-TO-USE.md) | [한국어](./HOW-TO-USE.md)

> 이 가이드는 **비개발자**를 위해 작성되었습니다. Python, Git, API를 몰라도 괜찮습니다. 질문을 타이핑할 수 있으면 이 도구를 사용할 수 있습니다.

---

## 필요한 것 (최초 1회 설정)

| 항목 | 이유 | 설치 방법 |
|------|------|---------|
| **Claude Code** | 에이전트를 실행하는 앱 | [시작하기](https://docs.anthropic.com/en/docs/claude-code/overview) — CLI, 데스크톱 앱, VS Code 확장 |
| **이 저장소** | 번역 에이전트와 언어 가이드 포함 | GitHub에서 다운로드 (아래 참조) |

### 선택 의존성

| 패키지 | 이유 | 설치 방법 |
|--------|------|---------|
| **python-docx** | DOCX 파싱 및 생성 | `pip install python-docx` |
| **pymupdf** | PDF 텍스트 추출 | `pip install pymupdf` |
| **pandoc** | 형식 변환 대체 수단 | [pandoc.org/installing](https://pandoc.org/installing.html) |
| **markitdown** | 비주류 형식 지원 (PPTX, XLSX, HTML 등) | `pip install 'markitdown[all]'` |

python-docx와 pymupdf는 DOCX/PDF 처리에 필수입니다. 나머지는 선택 사항입니다.

---

## 저장소 다운로드

### Git이 설치되어 있는 경우

```bash
git clone https://github.com/kipeum86/legal-translation-agent.git
```

### Git이 없는 경우

1. [github.com/kipeum86/legal-translation-agent](https://github.com/kipeum86/legal-translation-agent) 접속
2. 초록색 **"Code"** 버튼 클릭
3. **"Download ZIP"** 클릭
4. 원하는 폴더에 압축 해제

---

## 에이전트 시작하기

### 방법 A: 데스크톱 앱 / VS Code

1. Claude Code 실행
2. `legal-translation-agent` 폴더 열기
3. 에이전트가 자동 활성화 — **KP Legal Orchestrator**의 **법률 번역 스페셜리스트**와 바로 작업을 시작합니다

### 방법 B: 터미널 (CLI)

```bash
cd legal-translation-agent
claude
```

### 최초 설정

첫 세션에서 에이전트가 간단한 **온보딩 인터뷰**(`/setup`)를 진행합니다:

1. 이름, 소속, 역할
2. 주요 언어쌍 (예: 영어 → 한국어)
3. 주요 문서 유형 (NDA, 이용약관, 개인정보처리방침 등)
4. 기본 설정 (출력 형식, 번역 모드, 영어 관할 변형)
5. 선택 사항: Library 프로필 생성

설정은 `config.json`에 저장됩니다. `/setup`으로 언제든 재설정 가능합니다.

### 프라이빗 데이터 위치

원문 문서, 출력물, 비공개 Library 자산, 용어집, 내부 노트는 이제
리포지토리 바깥의 `$LEGAL_TRANSLATION_PRIVATE_DIR`에 보관합니다.

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"/{input,output/documents,output/working,library,glossary,_private}
```

자세한 설정: [PRIVATE-DIR-SETUP.md](./PRIVATE-DIR-SETUP.md)

---

## 문서 번역하기

### 빠른 시작

1. 문서를 `${LEGAL_TRANSLATION_PRIVATE_DIR}/input/`에 넣습니다
2. 에이전트에게 알려줍니다:

> "${LEGAL_TRANSLATION_PRIVATE_DIR}/input 에 있는 계약서 한국어로 번역해줘"

또는:

> "/translate"

### 지원 언어

5개 언어 모두 양방향 번역을 지원합니다:

| 언어 | 코드 | 법률 어체 |
|------|------|---------|
| 영어 | en | 공식 법률 문체 (US / UK / International) |
| 한국어 | ko | 문어체 (~한다, ~하여야 한다) |
| 중국어 간체 | zh-cn | 중국 대륙 규범 (民法典, 第N条/款/项) |
| 중국어 번체 | zh-tw | 대만 규범 (民法, 第N條/項/款) |
| 일본어 | ja | です/ます 또는 である (APPI 규범) |

### 지원 문서 유형

- **계약서류** — NDA, 라이선스 계약, 합작투자 계약, 공급 계약, 근로 계약
- **소비자 대상** — 이용약관, 개인정보처리방침, EULA, 쿠키 정책
- **기업·규제** — 정관, 규제 서류, 컴플라이언스 문서, 이사회 결의서
- **분쟁·소송** — 법률의견서, 합의서, 중재 조항
- **IP·기술** — 특허 라이선스, SaaS 계약, 데이터 처리 계약

### 지원 파일 형식

| 형식 | 읽기 | 쓰기 |
|------|:---:|:---:|
| `.docx` | 가능 | 가능 |
| `.pdf` | 가능 | — |
| `.md` | 가능 | 가능 |
| `.txt` | 가능 | 가능 |
| `.pptx`, `.xlsx`, `.html`, `.epub` | 가능 (markitdown 필요) | — |

---

## 두 가지 번역 모드

| 모드 | 동작 | 비용 | 사용 시점 |
|------|------|------|---------|
| **Normal** | 이중 패스 → 종합 → 구조 검증 | ~2.5배 | 일반 문서 — 기본값 |
| **Hard** | Normal + 역번역 + Library 비교 + 편집 교정 | ~5-6배 | 출판 수준, 고위험 번역 |

### Normal 모드 파이프라인 (Step 1~7)

1. **문서 분석** — 파싱, 언어 감지, 구조 카운트
2. **용어 설정** — 용어 추출, 용어집 로드, 작업 용어집 조립
3. **번역 패스 A** — 첫 번째 독립 번역
4. **번역 패스 B** — 두 번째 독립 번역 (새 컨텍스트, 패스 A 접근 불가)
5. **비교 종합** — 두 패스를 하나의 통일된 문체로 병합
6. **구조 검증** — 원문 대 번역문 구조 수량 비교 (결정론적)
7. **품질 게이트 & 출력** — 6개 항목 검사, 용어집 저장, 파일 생성

### Hard 모드 추가 과정 (Step 8~10)

8. **역번역** — 핵심 구간(30~50%)을 원문 언어로 역번역, 의미 변이 비교
9. **Library 참조 비교** — Library의 골드스탠다드 번역과 비교 (Library 자산 없으면 생략)
10. **편집 교정** — 원어민 수준 편집 검토, 10개 항목 품질 게이트

---

## 용어집 시스템 활용하기

에이전트는 번역 작업마다 자동으로 성장하는 **영속 용어집**을 유지합니다.

### 작동 방식

- 각 작업에서 추출된 용어가 `${LEGAL_TRANSLATION_PRIVATE_DIR}/glossary/glossary_{src}_{tgt}.json`에 저장됩니다
- 같은 언어쌍의 다음 번역 시 해당 용어가 자동으로 로드됩니다
- 용어집은 모든 번역에서 **일관된 용어**를 보장합니다

### 용어집 우선순위 (충돌 시)

같은 용어에 여러 매핑이 있을 때:

1. **Library 커스텀 용어집** — 최우선 (회사 전용 용어)
2. **영속 용어집** — 이전 번역에서 축적된 것
3. **LLM 제안** — 기존 매핑이 없을 때

### 용어집 관리하기

`/glossary` 명령을 사용하세요:

| 하위 명령 | 기능 |
|----------|------|
| `/glossary list` | 모든 용어집 파일과 용어 수 표시 |
| `/glossary show en-ko` | 영한 용어집 내용 표시 |
| `/glossary search "불법행위"` | 전체 용어집에서 검색 |
| `/glossary export en-ko --format xlsx` | 스프레드시트로 내보내기 |
| `/glossary import terms.json` | 외부 용어집 가져오기 |
| `/glossary edit en-ko "tort"` | 특정 용어 매핑 편집 |
| `/glossary stats` | 사용 통계 표시 |

---

## Library로 더 좋은 번역 얻기

Library는 특정 클라이언트나 프로젝트를 위한 **골드스탠다드 참조 번역**, 커스텀 용어집, 스타일 가이드를 저장합니다.

### Library 구조

```text
${LEGAL_TRANSLATION_PRIVATE_DIR}/library/
└── {프로필명}/
    ├── profile.json
    ├── inbox/              ← 새 파일을 여기에 넣고 ingest
    ├── references/
    │   └── en-ko/          ← 언어쌍 폴더
    │       ├── source/     ← 원본 문서 (English)
    │       └── target/     ← 골드스탠다드 번역본 (Korean)
    ├── glossaries/         ← 회사 전용 용어 매핑
    └── style-guides/       ← 번역 스타일 선호도
```

### Library 프로필 만들기

> "/library create-profile acme-corp"

디렉토리 구조가 생성됩니다. 온보딩(`/setup`) 중에도 설정할 수 있습니다.

### Ingest로 참조 번역 추가하기

**Ingest** 시스템은 참조 자료를 Library에 체계적으로 정리해 줍니다.

#### Step 1: 파일 넣기

참조 파일(DOCX, PDF, MD, TXT, PPTX, XLSX, HTML, EPUB 등)을 Library 프로필의 inbox에 넣습니다:

```text
${LEGAL_TRANSLATION_PRIVATE_DIR}/library/{프로필명}/inbox/
```

#### Step 2: Ingest 실행

> "library inbox에 파일 넣었어, ingest 해줘"

또는:

> "/library ingest {프로필명}"

#### Step 3: 분류

에이전트가 각 파일에 대해 물어봅니다:
- **언어쌍**: 예) `en-ko` (영어 → 한국어)
- **역할**: `source` (원본) 또는 `target` (골드스탠다드 번역본)

#### Step 4: 완료

에이전트가 자동으로:
1. 언어쌍 디렉토리가 없으면 **생성** (`references/en-ko/source/`, `references/en-ko/target/`)
2. inbox에서 적절한 하위 폴더로 파일 **이동**
3. 새 참조 항목으로 `profile.json` **업데이트**

#### 참조 번역이 사용되는 방식

- **Normal 모드**: 사용 안 함 (참조는 Hard 모드 전용)
- **Hard 모드 (Step 9)**: 현재 번역을 골드스탠다드 참조와 비교:
  - 용어 일관성
  - 어체/톤 정렬
  - 표현 선호도
  - 스타일 가이드 준수

정기적으로 번역하는 문서 유형과 가까운 참조 번역일수록 결과가 좋습니다.

### 기타 Library 명령

| 하위 명령 | 기능 |
|----------|------|
| `/library list` | 모든 프로필과 자산 수 표시 |
| `/library show {프로필}` | 프로필 상세 정보 및 자산 목록 표시 |
| `/library validate {프로필}` | 전체 자산 검사 (파일 가독성, 용어집 스키마, 스타일 형식) |

---

## 배치 번역

여러 관련 문서를 번역해야 할 때 배치 모드를 사용하세요:

> "/translate-batch"

### 작동 방식

1. **문서 1**: 전체 번역 파이프라인 실행, 작업 용어집 생성
2. **문서 2~N**: 누적 작업 용어집과 함께 전체 파이프라인 실행 (새 용어 추가, 기존 용어 고정)
3. **문서 간 일관성 검사**: 당사자명, 정의 용어, 날짜 형식, 법률 참조 표현을 문서 전체에서 확인
4. **최종 용어집 병합**: 모든 새 용어 저장

같은 거래의 관련 계약서 세트(예: NDA + 라이선스 계약 + SaaS 계약)를 번역할 때 이상적입니다.

---

## 중단된 작업 재개하기

번역이 중단되면 (연결 끊김, 세션 종료):

> "/resume"

에이전트는 매 파이프라인 단계 후 체크포인트를 저장합니다. 중단된 지점에서 정확히 재개됩니다.

---

## 좋은 결과를 위한 팁

### 언어쌍과 관할권을 구체적으로

| 이렇게 말고 | 이렇게 |
|-----------|--------|
| "이거 번역해줘" | "이 NDA 영어에서 한국어로 번역해줘" |
| "영어로 번역" | "이 개인정보처리방침 한국어에서 영어로 번역해줘, US 규범으로" |
| "중국어로" | "중국어 간체(중국 대륙 규범)로 번역해줘" |

### 용어집을 일찍 구축하기

용어집은 일관성을 위한 가장 강력한 도구입니다. 첫 몇 번의 번역 후:

1. `/glossary show {언어쌍}`으로 생성된 용어집 검토
2. `/glossary edit`로 잘못된 매핑 수정
3. `/glossary import`로 기존 사내 용어집 가져오기

### 고위험 문서에는 Hard 모드 사용

Normal 모드가 대부분의 업무에 충분합니다. Hard 모드를 사용할 때:
- 법원 제출이나 규제 기관 제출에 사용될 번역
- 클라이언트나 상대방이 번역에 직접 의존하는 경우
- 외부에 공개·배포되는 문서
- 기존 참조 번역과 비교가 필요한 경우

### 참조 번역 제공하기

과거에 고품질이라고 판단한 번역이 있다면 Library에 추가하세요. 참조 자료가 많을수록 Hard 모드의 Step 9(Library 비교)이 선호하는 스타일에 더 잘 맞출 수 있습니다.

---

## 이 도구가 하지 않는 것

- **법률 자문을 제공하지 않습니다.** 문서를 번역합니다. 법적 리스크 분석, 계약 검토, 전략 권고를 하지 않습니다.
- **공인 번역을 생성하지 않습니다.** 기계 보조 번역은 법적 절차에 사용하기 전 전문가 검토가 필요합니다.
- **문서를 작성하지 않습니다.** 기존 문서를 번역합니다. 작성이 필요하면 Legal Writing Agent를 사용하세요.
- **법률 조사를 하지 않습니다.** 법령, 판례, 규정을 검색하지 않습니다.
- **용어를 자동 업데이트하지 않습니다.** 용어집은 번역 작업에서 축적됩니다. 주기적으로 검토하고 관리하세요.

---

> **기억하세요:** 이것은 자동 조종이 아니라 파워 도구입니다. 법률 번역을 극적으로 빠르고 일관되게 만들어주지만, 최종 판단은 항상 자격을 갖춘 사람의 몫입니다.
