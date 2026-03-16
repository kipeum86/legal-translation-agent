# 법률문서 번역 에이전트

> **기계 보조 번역입니다. 사용 전 전문가 검토가 필요합니다.**

5개 언어 간 법률문서를 엄밀한 정확성, 일관성, 구조적 충실도로 번역하는 Claude Code 에이전트입니다.

---

## 개요

법무법인 진주를 위해 구축된 이 에이전트는 EULA, 이용약관, 개인정보처리방침, NDA, 라이선스 계약서, 규제 서류 등 법률문서의 출판 수준 번역을 제공합니다.

### 핵심 기능

- **무누락 보증** — 모든 조, 항, 호, 문장, 정의 용어가 빠짐없이 번역됩니다
- **이중 패스 번역** — 독립적인 두 번의 번역 후 비교 합성
- **관할권 인식 용어** — BGB, UCC, PRC, 대만, APPI 관행을 준수합니다
- **영구 용어집** — 매 번역마다 성장하는 법무법인 전체 번역 메모리
- **구조 검증** — 결정론적 카운팅으로 누락 방지

### 지원 언어

| 언어 | 코드 | 문체 |
|------|------|------|
| 영어 | `en` | 정식 법률 문체 (US / UK / International) |
| 한국어 | `ko` | 문어체 (~한다/~하여야 한다) |
| 간체 중국어 | `zh-cn` | PRC 관행 |
| 정체 중국어 | `zh-tw` | 대만 관행 |
| 일본어 | `ja` | です/ます 또는 である체 |

5개 언어 모두 양방향 번역을 지원합니다.

---

## 두 가지 모드

| 모드 | 파이프라인 | 비용 | 용도 |
|------|-----------|------|------|
| **Normal** | 이중 패스 → 합성 → 구조 검증 | ~2.5배 | 일반 문서 |
| **Hard** | Normal + 역번역 + Library 비교 + 편집 교정 | ~5-6배 | 출판급, 고위험 문서 |

Hard 모드는 Normal의 엄격한 상위집합입니다 — 검증 레이어를 추가하지, 제거하지 않습니다.

---

## 빠른 시작

### 1. 문서 배치

```bash
cp your-document.docx input/
```

지원 형식: `.docx`, `.pdf`, `.md`, `.txt`

### 2. 번역 실행

```
/translate
```

에이전트가 다음을 확인합니다:
- 대상 언어 (en / ko / zh-cn / zh-tw / ja)
- 모드 (기본값: Normal)
- 출력 형식 (채팅 / TXT / Markdown / DOCX)

### 3. 결과 확인

최종 번역물은 `output/documents/`에 저장됩니다:
```
{날짜}_{문서유형}_{원문}-to-{대상}_{모드}_v{버전}.{확장자}
```

---

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/translate` | 단일 문서 번역 (WF1) |
| `/translate-batch` | 공유 용어집으로 복수 문서 배치 번역 (WF4) |
| `/glossary` | 영구 용어집 관리 — list, show, search, export, import, edit (WF3) |
| `/library` | Library 프로필 관리 — list, show, ingest, create-profile, validate (WF2) |
| `/resume` | 중단된 번역 작업 재개 |

---

## 번역 파이프라인 (Normal 모드)

```
Step 1: 문서 수집 & 분석
    ↓
Step 2: 용어 추출 & 용어집 구성
    ↓
Step 3: 번역 Pass A  →  sub-agent (translator)
    ↓
Step 4: 번역 Pass B  →  sub-agent (translator, 독립 컨텍스트)
    ↓
Step 5: 비교 합성  →  sub-agent (synthesis-editor)
    ↓
Step 6: 구조 검증
    ↓
Step 7: 출력 조립 & 품질 게이트
```

Hard 모드는 Step 8-10을 추가합니다: 역번역 검증, Library 참조 비교, 편집 교정.

---

## 아키텍처

### Sub-Agent

| 에이전트 | 역할 | 호출 횟수 |
|---------|------|----------|
| `translator` | 독립적 번역 패스 생성 | Normal: 2회, Hard: 3회 |
| `synthesis-editor` | Pass A + B를 최종본으로 합성 | 1회 + 보정 |
| `editorial-reviewer` | 원어민 수준 편집 교정 (Hard 전용) | 1회 |

### Skill

| 스킬 | 기능 |
|------|------|
| `document-analyzer` | 파일 파싱, 언어 감지, 구조 인벤토리 |
| `terminology-manager` | 용어 추출, 용어집 계층, 머지 |
| `structural-verifier` | 원문 vs 번역문 결정론적 카운트 비교 |
| `back-translation-checker` | 핵심 조항 선별, 이탈도 분류 |
| `library-comparator` | 참조 번역 비교, 스타일 가이드 준수 |
| `output-generator` | 파일 조립, 형식 변환 |
| `quality-checker` | 6항목 (Normal) / 10항목 (Hard) 품질 게이트 |

---

## 용어집 시스템

영구 용어집은 에이전트의 핵심 누적 자산입니다 — 매 번역마다 성장합니다.

**계층** (충돌 시 우선순위):
1. **Library 커스텀 용어집** — 회사별 지정, 최우선
2. **영구 용어집** — 법무법인 전체, 자동 누적
3. **LLM 제안** — 기존 매핑 없을 때

용어집 파일은 `/glossary/`에 언어쌍별 JSON으로 저장됩니다.

---

## Library 시스템

Library는 회사/프로젝트별 참조 번역, 커스텀 용어집, 스타일 가이드의 사용자 관리 컬렉션입니다.

```
library/
└── {프로필명}/
    ├── profile.json
    ├── inbox/          # 새 자산 여기에 배치
    ├── references/     # 검수 완료 참조 번역
    ├── glossaries/     # 회사별 용어 매핑
    └── style-guides/   # 번역 스타일 가이드
```

에이전트는 Library 자산을 읽기만 하고 수정하지 않습니다.

---

## 프로젝트 구조

```
├── CLAUDE.md                          # 메인 오케스트레이터
├── .claude/
│   ├── skills/                        # 7개 스킬
│   ├── agents/                        # 3개 sub-agent
│   │   └── translator/references/     # 5개 언어 가이드
│   └── commands/                      # 5개 슬래시 커맨드
├── input/                             # 원본 문서 (gitignore)
├── output/                            # 번역 출력 (gitignore)
├── glossary/                          # 영구 용어집
└── library/                           # 사용자 관리 자산 (gitignore)
```

---

## 요구 사항

- [Claude Code](https://claude.ai/claude-code) CLI
- Python 3.8+ (구조 카운팅, 용어집 머지 스크립트용)
- 선택: `pandoc` (DOCX 출력), `python-docx` (DOCX 파싱 폴백)

---

## 라이선스

법무법인 진주 내부 도구. 외부 배포 불가.
