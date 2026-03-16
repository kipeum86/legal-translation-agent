# Legal Doc Translator Agent

> **Machine-assisted translation. Professional review required before use.**

A Claude Code agent that translates legal documents with strict accuracy, consistency, and structural fidelity across 5 languages.

**[한국어 README](README.ko.md)**

---

## Overview

Meet **변혁기 변호사 (Attorney Byeon Hyeok-gi)** — a 4th year associate at 법무법인 진주 (Law Firm Pearl) whose name sounds suspiciously like 번역기 (translator).

Handles any legal document that needs to cross language boundaries:
- **Contracts & agreements** — NDAs, license agreements, joint venture agreements, supply contracts, employment agreements
- **Consumer-facing legal** — terms of service, privacy policies, EULAs, cookie policies
- **Corporate & regulatory** — articles of incorporation, regulatory filings, compliance documents, board resolutions
- **Dispute & litigation** — legal opinions, settlement agreements, arbitration clauses
- **IP & technology** — patent license agreements, SaaS agreements, data processing agreements

### Key Capabilities

- **Zero-omission guarantee** — every article, sub-clause, sentence, and defined term is translated
- **Dual-pass translation** — two independent translation passes merged via comparative synthesis
- **Jurisdiction-aware terminology** — BGB, UCC, PRC, Taiwan, APPI conventions respected
- **Persistent glossary** — firm-wide translation memory that grows with every job
- **Structural verification** — deterministic counting ensures nothing is missed

### Supported Languages

| Language | Code | Register |
|----------|------|----------|
| English | `en` | Formal legal prose (US / UK / International) |
| Korean | `ko` | 문어체 (~한다/~하여야 한다) |
| Simplified Chinese | `zh-cn` | PRC conventions |
| Traditional Chinese | `zh-tw` | Taiwan conventions |
| Japanese | `ja` | です/ます or である体 |

All 5 languages support bidirectional translation.

---

## Two Operating Modes

| Mode | Pipeline | Cost | Use Case |
|------|----------|------|----------|
| **Normal** | Dual-pass → synthesis → structural verification | ~2.5x | Standard documents |
| **Hard** | Normal + back-translation + Library comparison + editorial polish | ~5-6x | Publication-grade, high-stakes documents |

Hard mode is a strict superset of Normal — it adds verification layers, never removes them.

---

## Quick Start

### 1. Place your document

```bash
cp your-document.docx input/
```

Supported formats: `.docx`, `.pdf`, `.md`, `.txt`

### 2. Run translation

```
/translate
```

The agent will ask for:
- Target language (en / ko / zh-cn / zh-tw / ja)
- Mode (Normal by default)
- Output format (Chat / TXT / Markdown / DOCX)

### 3. Review output

Final translations are saved to `output/documents/` with the naming convention:
```
{date}_{doctype}_{src}-to-{tgt}_{mode}_v{N}.{ext}
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/setup` | First-time onboarding interview or reconfigure settings |
| `/translate` | Translate a single document (WF1) |
| `/translate-batch` | Translate multiple documents with shared glossary (WF4) |
| `/glossary` | Manage persistent glossaries — list, show, search, export, import, edit (WF3) |
| `/library` | Manage Library profiles — list, show, ingest, create-profile, validate (WF2) |
| `/resume` | Resume an interrupted translation from checkpoint |

---

## Translation Pipeline (Normal Mode)

```
Step 1: Document Ingestion & Analysis
    ↓
Step 2: Terminology Extraction & Glossary Setup
    ↓
Step 3: Translation Pass A  →  sub-agent (translator)
    ↓
Step 4: Translation Pass B  →  sub-agent (translator, fresh context)
    ↓
Step 5: Comparative Synthesis  →  sub-agent (synthesis-editor)
    ↓
Step 6: Structural Verification
    ↓
Step 7: Output Assembly & Quality Gate
```

Hard mode adds Steps 8-10: back-translation verification, Library reference comparison, and editorial polish.

---

## Architecture

### Sub-Agents

| Agent | Role | Invocations |
|-------|------|-------------|
| `translator` | Produce independent translation passes | Normal: 2, Hard: 3 |
| `synthesis-editor` | Merge Pass A + B into final translation | 1 + remediation |
| `editorial-reviewer` | Native-speaker editorial polish (Hard only) | 1 |

### Skills

| Skill | Function |
|-------|----------|
| `document-analyzer` | Parse files, detect language, build structural inventory |
| `terminology-manager` | Term extraction, glossary hierarchy, merge |
| `structural-verifier` | Deterministic source vs target count comparison |
| `back-translation-checker` | Critical segment selection, divergence classification |
| `library-comparator` | Reference comparison, style guide compliance |
| `output-generator` | File assembly, format conversion |
| `quality-checker` | 6-item (Normal) / 10-item (Hard) quality gates |

---

## Glossary System

The persistent glossary is the agent's core accumulating asset — it grows with every translation.

**Hierarchy** (conflict resolution order):
1. **Library custom glossary** — company-specific, highest priority
2. **Persistent glossary** — firm-wide, auto-accumulated
3. **LLM proposal** — when no prior mapping exists

Glossary files are stored in `/glossary/` as JSON, one file per language pair.

---

## Library System

The Library is a user-managed collection of reference translations, custom glossaries, and style guides per company or project.

```
library/
└── {profile-name}/
    ├── profile.json
    ├── inbox/          # Drop new assets here
    ├── references/     # Gold-standard translations
    ├── glossaries/     # Company-specific term mappings
    └── style-guides/   # Translation style preferences
```

The agent reads Library assets but never modifies them.

---

## Project Structure

```
├── CLAUDE.md                          # Main orchestrator
├── .claude/
│   ├── skills/                        # 7 specialized skills
│   │   ├── document-analyzer/
│   │   ├── terminology-manager/
│   │   ├── structural-verifier/
│   │   ├── back-translation-checker/
│   │   ├── library-comparator/
│   │   ├── output-generator/
│   │   └── quality-checker/
│   ├── agents/                        # 3 sub-agents
│   │   ├── translator/
│   │   │   └── references/            # 5 language guides
│   │   ├── synthesis-editor/
│   │   └── editorial-reviewer/
│   └── commands/                      # 5 slash commands
├── input/                             # Source documents (gitignored)
├── output/                            # Translation output (gitignored)
├── glossary/                          # Persistent glossary store
└── library/                           # User-managed assets (gitignored)
```

---

## Requirements

- [Claude Code](https://claude.ai/claude-code) CLI
- Python 3.8+ (for structural counting, glossary merge scripts)
- Optional: `pandoc` (for DOCX output), `python-docx` (fallback DOCX parsing)

---

## License

Internal tool for 법무법인 진주. Not for public distribution.
