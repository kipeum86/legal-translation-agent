# 프라이빗 디렉토리 설정

이 에이전트의 모든 사용자 데이터는 리포지토리 **바깥**의
`$LEGAL_TRANSLATION_PRIVATE_DIR` 경로에 보관됩니다. 리포지토리 자체에는
코드, 문서, 스캐폴딩만 포함됩니다.

## 최초 설정

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"/{input,output/documents,output/working,library,glossary,_private}
```

`~/.zshrc` 또는 `~/.bashrc`에 `export` 줄을 추가해 두시면 영구 설정됩니다.

## 구조

```text
$LEGAL_TRANSLATION_PRIVATE_DIR/
├── input/          ← 원문 문서
├── output/
│   ├── documents/  ← 최종 번역 문서
│   └── working/    ← 중간 산출물 (checkpoint.json, pass-a.md 등)
├── library/        ← 사용자 관리 레퍼런스·용어집·스타일 가이드
├── glossary/       ← 영속 용어집
└── _private/       ← 내부 작업 산출물 (설계 문서, 노트 등)
```

## 왜 리포 안에 두지 않나요?

원문 법률 문서와 자체 용어집은 기밀 자료입니다. 리포지토리 바깥에
보관함으로써 실수로 `git add --force`를 실행하거나 잘못된 브랜치를
푸시했을 때 유출될 가능성을 원천 차단합니다.
