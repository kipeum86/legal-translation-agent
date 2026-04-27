# How to Use the Legal Translation Agent

[English](./HOW-TO-USE.md) | [한국어](../ko/HOW-TO-USE.md)

> This guide is written for **non-developers**. You don't need to understand Python, Git, or APIs. If you can type a question, you can use this tool.

---

## What You Need (One-Time Setup)

| What | Why | How to Get It |
|------|-----|---------------|
| **Claude Code** | This is the app that runs the agent | [Get started here](https://docs.anthropic.com/en/docs/claude-code/overview) — available as CLI, desktop app, or VS Code extension |
| **This repository** | Contains the translation agent and language guides | Download from GitHub (see below) |

### Optional Dependencies

| Package | Why | How to Get It |
|---------|-----|---------------|
| **python-docx** | DOCX parsing and generation | `pip install python-docx` |
| **pymupdf** | PDF text extraction | `pip install pymupdf` |
| **pandoc** | Format conversion fallback | [pandoc.org/installing](https://pandoc.org/installing.html) |
| **markitdown** | Non-core format support (PPTX, XLSX, HTML, etc.) | `pip install 'markitdown[all]'` |

python-docx and pymupdf are required for DOCX/PDF handling. The others are optional.

---

## Downloading the Repository

### If you have Git installed

```bash
git clone https://github.com/kipeum86/legal-translation-agent.git
```

### If you don't have Git

1. Go to [github.com/kipeum86/legal-translation-agent](https://github.com/kipeum86/legal-translation-agent)
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Unzip to a folder of your choice

---

## Starting the Agent

### Option A: Desktop App / VS Code

1. Open Claude Code
2. Open the `legal-translation-agent` folder
3. The agent activates automatically — you'll be working with the **Legal Translation Specialist** from **KP Legal Orchestrator**

### Option B: Terminal (CLI)

```bash
cd legal-translation-agent
claude
```

### First-Time Setup

On your first session, the agent runs a brief **onboarding interview** (`/setup`):

1. Your name, affiliation, and role
2. Primary language pairs (e.g., English → Korean)
3. Common document types (NDA, ToS, privacy policy, etc.)
4. Default settings (output format, translation mode, English variant)
5. Optional: create a Library profile

Settings are saved to `${LEGAL_TRANSLATION_PRIVATE_DIR}/config.json`. Re-run anytime with `/setup`.

### Private Data Location

Source documents, outputs, private Library assets, glossaries, and
internal notes now live outside the repo at
`$LEGAL_TRANSLATION_PRIVATE_DIR`.

```bash
export LEGAL_TRANSLATION_PRIVATE_DIR="$HOME/legal-translation-private"
mkdir -p "$LEGAL_TRANSLATION_PRIVATE_DIR"/{input,output/documents,output/working,library,glossary,_private}
```

Detailed setup: [PRIVATE-DIR-SETUP.md](./PRIVATE-DIR-SETUP.md)

---

## Translating a Document

### Quick Start

1. Place your document in `${LEGAL_TRANSLATION_PRIVATE_DIR}/input/`
2. Tell the agent:

> "${LEGAL_TRANSLATION_PRIVATE_DIR}/input 에 있는 계약서 한국어로 번역해줘"

or:

> "/translate"

### Supported Languages

All 5 languages support bidirectional translation:

| Language | Code | Legal Register |
|----------|------|---------------|
| English | en | Formal legal prose (US / UK / International) |
| Korean | ko | 문어체 (~한다, ~하여야 한다) |
| Simplified Chinese | zh-cn | PRC conventions (民法典, 第N条/款/项) |
| Traditional Chinese | zh-tw | Taiwan conventions (民法, 第N條/項/款) |
| Japanese | ja | です/ます or である (APPI conventions) |

### Document Types Handled

- **Contracts & agreements** — NDAs, license agreements, JVAs, supply contracts, employment agreements
- **Consumer-facing legal** — terms of service, privacy policies, EULAs, cookie policies
- **Corporate & regulatory** — articles of incorporation, regulatory filings, compliance documents, board resolutions
- **Dispute & litigation** — legal opinions, settlement agreements, arbitration clauses
- **IP & technology** — patent licenses, SaaS agreements, data processing agreements

### Supported File Formats

| Format | Read | Write |
|--------|:----:|:-----:|
| `.docx` | Yes | Yes |
| `.pdf` | Yes | — |
| `.md` | Yes | Yes |
| `.txt` | Yes | Yes |
| `.pptx`, `.xlsx`, `.html`, `.epub` | Yes (with markitdown) | — |

---

## Three Translation Modes

| Mode | What It Does | Cost | When to Use |
|------|-------------|------|-------------|
| **Fast** | Single draft → deterministic structure/glossary checks | ~1x base | Internal drafts only |
| **Normal** | Differentiated dual-pass → synthesis → structural verification | ~2.5x base | Standard documents — default |
| **Hard** | Normal + back-translation + Library comparison + editorial polish | ~5-6x base | Publication-grade, high-stakes translations |

### Fast Mode Draft Flow (Steps 1–5)

Fast mode runs document analysis, terminology setup, one translation draft, deterministic structure/glossary checks, and draft output assembly. It skips Pass B and synthesis, so the output must remain labeled as draft / internal review only.

### Normal Mode Pipeline (Steps 1–7)

1. **Document Analysis** — parse, detect language, count structures
2. **Terminology Setup** — extract terms, load glossaries, assemble working glossary
3. **Translation Pass A** — first independent translation
4. **Translation Pass B** — second independent translation (fresh context, no access to Pass A)
5. **Comparative Synthesis** — merge both passes into one voice
6. **Structural Verification** — deterministic count comparison (source vs. target)
7. **Quality Gate & Output** — 6-item check, glossary persistence, file generation

### Hard Mode Adds (Steps 8–10)

8. **Back-Translation** — reverse-translate 30-50% of critical segments back to source, compare for semantic drift
9. **Library Reference Comparison** — compare against gold-standard translations from your Library (skip if no Library assets)
10. **Editorial Polish** — native-speaker editorial review, 10-item quality gate

---

## Using the Glossary System

The agent maintains a **persistent glossary** that grows with every translation job.

### How It Works

- Terms extracted during each job are saved to `${LEGAL_TRANSLATION_PRIVATE_DIR}/glossary/glossary_{src}_{tgt}.json`
- Next time you translate the same language pair, those terms are automatically loaded
- The glossary ensures **consistent terminology** across all your translations

### Glossary Hierarchy (Conflict Resolution)

When the same term has multiple mappings:

1. **Library custom glossary** — highest priority (your company-specific terms)
2. **Persistent glossary** — accumulated from prior translations
3. **LLM proposal** — when no prior mapping exists

### Managing Your Glossary

Use the `/glossary` command:

| Sub-Command | What It Does |
|-------------|-------------|
| `/glossary list` | List all glossary files with term counts |
| `/glossary show en-ko` | Display English-Korean glossary contents |
| `/glossary search "tort"` | Search across all glossaries |
| `/glossary export en-ko --format xlsx` | Export to spreadsheet |
| `/glossary import terms.json` | Import external glossary |
| `/glossary edit en-ko "tort"` | Edit a specific term mapping |
| `/glossary stats` | Show usage statistics |

---

## Using the Library for Better Translations

The Library stores **gold-standard reference translations**, custom glossaries, and style guides for specific clients or projects.

### Library Structure

```text
$LEGAL_TRANSLATION_PRIVATE_DIR/library/
└── {profile-name}/
    ├── profile.json
    ├── inbox/              ← Drop new files here for ingest
    ├── references/
    │   └── en-ko/          ← Language-pair folder
    │       ├── source/     ← Original documents (English)
    │       └── target/     ← Gold-standard translations (Korean)
    ├── glossaries/         ← Company-specific term mappings
    └── style-guides/       ← Translation style preferences
```

### Creating a Library Profile

> "/library create-profile acme-corp"

This creates the directory structure. You can also set this up during onboarding (`/setup`).

### Adding Reference Translations with Ingest

The **ingest** system helps you organize reference materials into your Library:

#### Step 1: Drop the file

Place any reference file (DOCX, PDF, MD, TXT, PPTX, XLSX, HTML, EPUB, etc.) into your Library profile's inbox:

```text
${LEGAL_TRANSLATION_PRIVATE_DIR}/library/{profile-name}/inbox/
```

#### Step 2: Run ingest

> "library inbox에 파일 넣었어, ingest 해줘"

or:

> "/library ingest {profile-name}"

#### Step 3: Classify

The agent asks you for each file:
- **Language pair**: e.g., `en-ko` (English → Korean)
- **Role**: `source` (original) or `target` (gold-standard translation)

#### Step 4: Done

The agent will:
1. **Create** the language-pair directory if it doesn't exist (`references/en-ko/source/`, `references/en-ko/target/`)
2. **Move** the file from inbox to the appropriate subfolder
3. **Update** the `profile.json` with the new reference entry

#### How Reference Translations Are Used

- **Normal mode**: Not used (references are Hard mode only)
- **Hard mode (Step 9)**: The agent compares your current translation against gold-standard references for:
  - Terminology consistency
  - Register/tone alignment
  - Phrasing preferences
  - Style guide compliance

The closer your reference translations match the type of documents you regularly translate, the better the results.

### Other Library Commands

| Sub-Command | What It Does |
|-------------|-------------|
| `/library list` | List all profiles with asset counts |
| `/library show {profile}` | Display profile details and asset manifest |
| `/library validate {profile}` | Check all assets (file readability, glossary schema, style format) |

---

## Batch Translation

Translating multiple related documents? Use batch mode:

> "/translate-batch"

### How It Works

1. **Plan**: Create a dry-run batch plan with local-script and LLM concurrency limits
2. **Phase 1**: Parse, structure-count, and extract term candidates for all documents in parallel
3. **Review**: Approve `batch-glossary-review.json`; party names and defined terms are locked before translation
4. **Phase 3**: Translate documents in parallel using the approved batch-level locks
5. **Cross-document consistency**: Party names, defined terms, date formats, and legal reference phrasing checked across all documents
6. **Final glossary merge**: All new terms persisted at the end

This is ideal for translating a set of related agreements (e.g., an NDA + License Agreement + SaaS Agreement for the same deal).

---

## Resuming Interrupted Work

If a translation is interrupted (connection lost, session ended):

> "/resume"

The agent saves checkpoints after every pipeline step. Resume picks up exactly where you left off.

---

## Tips for Best Results

### Be Specific About Language Pair and Jurisdiction

| Instead of | Try |
|-----------|-----|
| "Translate this" | "Translate this NDA from English to Korean" |
| "번역해줘" | "이 개인정보처리방침 영어에서 일본어로 번역해줘" |
| "English to Chinese" | "English to Simplified Chinese (PRC conventions)" |

### Build Your Glossary Early

The glossary is your most powerful tool for consistency. After your first few translations:

1. Review the generated glossary with `/glossary show {lang-pair}`
2. Fix any incorrect mappings with `/glossary edit`
3. Import existing firm glossaries with `/glossary import`

### Use Hard Mode for High-Stakes Documents

Normal mode is sufficient for most work. Use Hard mode when:
- The translation will be used in court filings or regulatory submissions
- Client or counterparty will rely directly on the translation
- The document will be published or distributed externally
- You need the translation compared against existing reference translations

Use Fast mode only when you need a quick internal draft and a qualified reviewer will still check the result before reliance.

### Provide Reference Translations

If you have past translations that you consider high-quality, add them to the Library. The more reference material you provide, the better Hard mode's Step 9 (Library comparison) can align the output to your preferred style.

---

## What This Tool Does NOT Do

- **It does not provide legal advice.** It translates documents. It does not analyze legal risk, review contracts, or recommend strategies.
- **It does not produce certified translations.** Machine-assisted output requires professional review before use in legal proceedings.
- **It does not draft documents.** It translates existing documents. For drafting, use the Legal Writing Agent.
- **It does not conduct legal research.** It does not search for statutes, cases, or regulations.
- **It does not automatically update terminology.** Glossaries are accumulated from your translations. Review and curate them periodically.

---

> **Remember:** This is a power tool, not an autopilot. It makes legal translation dramatically faster and more consistent, but the final judgment always belongs to a qualified human.
