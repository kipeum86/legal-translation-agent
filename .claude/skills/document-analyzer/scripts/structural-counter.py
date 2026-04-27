#!/usr/bin/env python3
"""
structural-counter.py — Deterministic structural element counter for legal documents.

Counts articles, sub-clauses, enumerated items, defined terms, and footnotes
across 5 languages: EN, KO, ZH-CN, ZH-TW, JA.

Used at Step 1 (source inventory) and Step 6 (target verification).

Usage:
    python3 structural-counter.py <input_file> <language_code> <output_path>

Language codes: en, ko, zh-cn, zh-tw, ja
Output: structural-inventory.json
"""

import json
import re
import sys
from pathlib import Path
from collections import OrderedDict

TERMINOLOGY_SCRIPTS = Path(__file__).resolve().parents[2] / "terminology-manager" / "scripts"
sys.path.insert(0, str(TERMINOLOGY_SCRIPTS))

from term_patterns import unique_terms  # noqa: E402

# ─── Language-specific patterns ───────────────────────────────────────────

ARTICLE_PATTERNS = {
    "en": [
        r"^(?:\*{0,2})(?:Article|ARTICLE)\s+(\d+(?:\.\d+)*)",
        r"^(?:\*{0,2})(?:Section|SECTION)\s+(\d+(?:\.\d+)*)",
    ],
    "ko": [
        r"^제\s*(\d+)\s*조",
    ],
    "zh-cn": [
        r"^第\s*([一二三四五六七八九十百零\d]+)\s*条",
    ],
    "zh-tw": [
        r"^第\s*([一二三四五六七八九十百零\d]+)\s*條",
    ],
    "ja": [
        r"^第\s*([一二三四五六七八九十百零\d]+)\s*条",
    ],
}

SUB_CLAUSE_PATTERNS = {
    "en": [
        r"^\s*(?:Section\s+)?\d+\.\d+",             # Section 1.1 / N.M paragraphs (항)
        r"^\s*\(\s*[ivxlc]+\s*\)",                    # (i), (ii), (iii)
    ],
    "ko": [
        r"^\s*(?:제\s*\d+\s*항|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])",  # 제X항 or circled numbers
    ],
    "zh-cn": [
        r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*款",   # 第X款
        r"^\s*[\(（]\s*[一二三四五六七八九十]+\s*[\)）]",  # (一) (二) (三)
    ],
    "zh-tw": [
        r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*項",   # 第X項
        r"^\s*[\(（]\s*[一二三四五六七八九十]+\s*[\)）]",  # (一) (二) (三)
    ],
    "ja": [
        r"^\s*(\d+)\s+",                               # Numbered paragraphs (項)
        r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]",                        # Circled numbers
    ],
}

ENUMERATED_ITEM_PATTERNS = {
    "en": [
        r"^\s*\(\s*[a-z]\s*\)",                        # (a), (b), (c) — enumerated items (호)
        r"^\s*\(\s*[A-Z]\s*\)",                        # (A), (B), (C)
        r"^\s*\(\s*\d+\s*\)",                          # (1), (2), (3)
        r"^\s*[a-z]\.\s",                              # a. b. c.
    ],
    "ko": [
        r"^\s*(?:제\s*\d+\s*호)",                       # 제X호
        r"^\s*(\d+)\.\s",                               # 1. 2. 3. (호)
        r"^\s*[가나다라마바사아자차카타파하]\.",            # 가. 나. 다.
        r"^\s*[\(（][가나다라마바사아자차카타파하][\)）]",   # (가) (나) (다)
    ],
    "zh-cn": [
        r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*项",    # 第X项
        r"^\s*\d+[\.\、]",                              # 1. 2. or 1、2、
    ],
    "zh-tw": [
        r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*款",    # 第X款 (sub-paragraph in TW)
        r"^\s*\d+[\.\、]",                              # 1. 2. or 1、2、
    ],
    "ja": [
        r"^\s*第?\s*[一二三四五六七八九十]+\s*号",         # 第X号 or X号
        r"^\s*[イロハニホヘトチリヌ][\s\.]",              # イ ロ ハ (katakana sub-items)
    ],
}

FOOTNOTE_PATTERNS = {
    "en": [r"\[\s*(\d+)\s*\]", r"\*{1,3}"],
    "ko": [r"\[\s*(\d+)\s*\]", r"각주\s*(\d+)"],
    "zh-cn": [r"\[\s*(\d+)\s*\]"],
    "zh-tw": [r"\[\s*(\d+)\s*\]"],
    "ja": [r"\[\s*(\d+)\s*\]", r"注\s*(\d+)"],
}


def normalize_language(lang: str) -> str:
    """Normalize language code to one of: en, ko, zh-cn, zh-tw, ja."""
    lang = lang.lower().strip()
    aliases = {
        "en": "en", "eng": "en", "english": "en",
        "ko": "ko", "kor": "ko", "korean": "ko",
        "zh-cn": "zh-cn", "zhs": "zh-cn", "zh_cn": "zh-cn", "chinese-simplified": "zh-cn",
        "zh-tw": "zh-tw", "zht": "zh-tw", "zh_tw": "zh-tw", "chinese-traditional": "zh-tw",
        "ja": "ja", "ja-jp": "ja", "jpn": "ja", "japanese": "ja", "ja_jp": "ja",
    }
    if lang in aliases:
        return aliases[lang]
    raise ValueError(f"Unsupported language code: {lang}. Supported: en, ko, zh-cn, zh-tw, ja")


def strip_markdown(line: str) -> str:
    """Strip common markdown formatting (bold, italic, headings) for pattern matching."""
    s = line.strip()
    s = re.sub(r"\*{1,3}", "", s)   # bold / italic markers
    s = re.sub(r"^#{1,6}\s+", "", s)  # heading markers
    return s.strip()


def cjk_number_to_int(value: str) -> int | None:
    """Convert simple CJK numerals up to hundreds to an integer."""
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)

    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "兩": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100}

    total = 0
    current = 0
    saw_unit = False
    for char in value:
        if char in digits:
            current = digits[char]
        elif char in units:
            saw_unit = True
            unit = units[char]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
        else:
            return None
    total += current
    if total == 0 and not saw_unit:
        return None
    return total


def canonical_article_id(article_number: str) -> str:
    """Build a cross-language comparable article identifier."""
    normalized = cjk_number_to_int(article_number)
    if normalized is None:
        normalized_text = re.sub(r"\s+", "", article_number.lower())
    else:
        normalized_text = str(normalized)
    return f"article:{normalized_text}"


def count_matches(text: str, patterns: list[str], per_line: bool = True) -> list[dict]:
    """Count regex matches. Returns list of {line, match} dicts."""
    results = []
    if per_line:
        for i, line in enumerate(text.split("\n"), 1):
            clean = strip_markdown(line)
            for pattern in patterns:
                if re.search(pattern, clean):
                    results.append({"line": i, "text": line.strip()})
                    break  # One match per line
    else:
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                results.append({"position": m.start(), "text": m.group()})
    return results


def extract_articles(text: str, lang: str) -> list[dict]:
    """Extract articles with their line positions."""
    patterns = ARTICLE_PATTERNS.get(lang, [])
    articles = []
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        clean = strip_markdown(line)
        for pattern in patterns:
            m = re.search(pattern, clean)
            if m:
                article_id = m.group(0).strip()
                article_number = m.group(1).strip()
                articles.append({
                    "id": article_id,
                    "canonical_id": canonical_article_id(article_number),
                    "line": i,
                    "raw_text": line.strip(),
                })
                break
    return articles


def count_sub_clauses_for_article(text_block: str, lang: str) -> int:
    """Count sub-clauses within an article text block."""
    patterns = SUB_CLAUSE_PATTERNS.get(lang, [])
    count = 0
    for line in text_block.split("\n"):
        clean = strip_markdown(line)
        for pattern in patterns:
            if re.search(pattern, clean):
                count += 1
                break
    return count


def count_enumerated_items_for_article(text_block: str, lang: str) -> int:
    """Count enumerated items within an article text block."""
    patterns = ENUMERATED_ITEM_PATTERNS.get(lang, [])
    count = 0
    for line in text_block.split("\n"):
        clean = strip_markdown(line)
        for pattern in patterns:
            if re.search(pattern, clean):
                count += 1
                break
    return count


def extract_defined_terms(text: str, lang: str) -> list[str]:
    """Extract unique defined terms from the document."""
    return unique_terms(text, lang)


def count_footnotes(text: str, lang: str) -> int:
    """Count footnotes in the document."""
    patterns = FOOTNOTE_PATTERNS.get(lang, [])
    footnote_nums = set()
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            try:
                footnote_nums.add(m.group(1))
            except IndexError:
                footnote_nums.add(m.group(0))
    return len(footnote_nums)


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~1.3 tokens per word (EN) or ~1.5 per character cluster (CJK)."""
    # Simple heuristic: count words + CJK characters
    words = len(re.findall(r"[a-zA-Z]+", text))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]", text))
    return int(words * 1.3 + cjk_chars * 1.5)


def build_article_blocks(text: str, articles: list[dict]) -> list[tuple]:
    """Split text into blocks per article for per-article counting."""
    lines = text.split("\n")
    blocks = []
    for i, article in enumerate(articles):
        start = article["line"] - 1  # 0-indexed
        end = articles[i + 1]["line"] - 1 if i + 1 < len(articles) else len(lines)
        block_text = "\n".join(lines[start:end])
        blocks.append((article, block_text))
    return blocks


def decide_segmentation(token_estimate: int, articles: list[dict]) -> tuple[bool, list[dict]]:
    """Decide if segmentation is needed and create segment plan."""
    THRESHOLD = 8000
    if token_estimate <= THRESHOLD:
        return False, []

    # Segment by article boundaries, targeting ~4000-6000 tokens per segment
    segments = []
    current_segment = {"id": "seg_01", "articles": [], "token_estimate": 0}
    seg_count = 1

    # Simple heuristic: distribute articles evenly
    avg_tokens_per_article = token_estimate // max(len(articles), 1)
    target_per_segment = THRESHOLD * 0.7  # ~5600 tokens per segment

    for article in articles:
        current_segment["articles"].append(article["id"])
        current_segment["token_estimate"] += avg_tokens_per_article

        if current_segment["token_estimate"] >= target_per_segment:
            segments.append(current_segment)
            seg_count += 1
            current_segment = {
                "id": f"seg_{seg_count:02d}",
                "articles": [],
                "token_estimate": 0,
            }

    # Add remaining articles
    if current_segment["articles"]:
        segments.append(current_segment)

    return True, segments


def build_inventory(input_file: str, lang: str) -> dict:
    """Build the complete structural inventory."""
    text = Path(input_file).read_text(encoding="utf-8")
    lang = normalize_language(lang)

    # Extract articles
    articles = extract_articles(text, lang)
    article_blocks = build_article_blocks(text, articles)

    # Per-article counting
    article_details = []
    total_sub_clauses = 0
    total_enumerated = 0

    for article_info, block_text in article_blocks:
        sub_count = count_sub_clauses_for_article(block_text, lang)
        enum_count = count_enumerated_items_for_article(block_text, lang)
        total_sub_clauses += sub_count
        total_enumerated += enum_count
        article_details.append({
            "id": article_info["id"],
            "canonical_id": article_info["canonical_id"],
            "sub_clauses": sub_count,
            "enumerated_items": enum_count,
        })

    # Document-level extractions
    defined_terms = extract_defined_terms(text, lang)
    footnotes = count_footnotes(text, lang)
    token_estimate = estimate_tokens(text)

    # Segmentation decision
    seg_required, segments = decide_segmentation(token_estimate, articles)

    inventory = OrderedDict([
        ("source_language", lang),
        ("total_articles", len(articles)),
        ("articles", article_details),
        ("total_sub_clauses", total_sub_clauses),
        ("total_enumerated_items", total_enumerated),
        ("defined_terms", defined_terms),
        ("defined_term_count", len(defined_terms)),
        ("footnotes", footnotes),
        ("estimated_tokens", token_estimate),
        ("segmentation_required", seg_required),
        ("segments", segments),
    ])

    return inventory


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 structural-counter.py <input_file> <language_code> <output_path>")
        print("Language codes: en, ko, zh-cn, zh-tw, ja")
        sys.exit(1)

    input_file = sys.argv[1]
    lang = sys.argv[2]
    output_path = sys.argv[3]

    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        inventory = build_inventory(input_file, lang)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Write output
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Structural inventory written to: {output_path}")
    print(f"  Articles: {inventory['total_articles']}")
    print(f"  Sub-clauses: {inventory['total_sub_clauses']}")
    print(f"  Enumerated items: {inventory['total_enumerated_items']}")
    print(f"  Defined terms: {inventory['defined_term_count']}")
    print(f"  Footnotes: {inventory['footnotes']}")
    print(f"  Estimated tokens: {inventory['estimated_tokens']}")
    print(f"  Segmentation required: {inventory['segmentation_required']}")


if __name__ == "__main__":
    main()
