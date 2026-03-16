# Glossary Entry Schema

JSON schema for glossary entries used in working glossary and persistent glossary.

## Entry Schema

```json
{
  "source_term": "Confidential Information",
  "target_term": "비밀정보",
  "source_lang": "en",
  "target_lang": "ko",
  "context": "Defined in Article 1.1 of NDA",
  "origin": "persistent",
  "library_profile": null,
  "alternatives_considered": ["기밀정보", "비밀 정보"],
  "selection_rationale": "법제처 표준 용어 + 실무 관행상 '비밀정보'가 가장 보편적",
  "status": "confirmed",
  "last_used": "2026-03-16",
  "usage_count": 5
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_term` | string | Yes | Term in source language |
| `target_term` | string | Yes | Translated term in target language |
| `source_lang` | string | Yes | Source language code (en, ko, zh-cn, zh-tw, ja) |
| `target_lang` | string | Yes | Target language code |
| `context` | string | No | Where the term is defined or first used |
| `origin` | string | Yes | One of: `"persistent"`, `"library"`, `"llm"` |
| `library_profile` | string | No | Library profile name if origin is "library" |
| `alternatives_considered` | array | No | Other translations considered |
| `selection_rationale` | string | No | Why this translation was chosen |
| `status` | string | Yes | One of: `"confirmed"`, `"tentative"` |
| `last_used` | string | No | ISO date of last use (YYYY-MM-DD) |
| `usage_count` | integer | No | Number of times used across translations |

## Origin Values

| Origin | Meaning | Priority | Persisted? |
|--------|---------|----------|------------|
| `library` | From Library custom glossary (company-specific) | Highest | No (session-only) |
| `persistent` | From persistent glossary (`/glossary/`) | Medium | Yes |
| `llm` | Newly proposed by LLM during this session | Lowest | Yes (after merge) |

## File Format

Persistent glossary files (`/glossary/glossary_{src}_{tgt}.json`):

```json
{
  "language_pair": "en_ko",
  "last_updated": "2026-03-16",
  "entry_count": 150,
  "entries": [ ... ]
}
```

Working glossary files (`/output/working/working-glossary.json`):

```json
{
  "source_lang": "en",
  "target_lang": "ko",
  "library_profile": "acme-corp",
  "entries": [ ... ]
}
```
