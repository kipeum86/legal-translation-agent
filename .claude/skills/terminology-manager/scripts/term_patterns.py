"""Shared term extraction patterns for legal translation artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TermHit:
    term: str
    pattern_id: str
    candidate_type: str
    line: int
    context: str


@dataclass(frozen=True)
class TermPattern:
    pattern_id: str
    regex: re.Pattern[str]
    candidate_type: str = "defined_term"


DEFINED_TERM_PATTERNS: dict[str, list[TermPattern]] = {
    "en": [
        TermPattern("en.quoted", re.compile(r'"([^"]{2,60})"')),
        TermPattern("en.smart_quoted", re.compile(r"\u201c([^\u201d]{2,60})\u201d")),
        TermPattern(
            "en.means",
            re.compile(r'"?([A-Z][A-Za-z0-9&,\-/]*(?:\s+[A-Z][A-Za-z0-9&,\-/]*){0,7})"?\s+means\b'),
        ),
        TermPattern(
            "en.refers_to",
            re.compile(r'"?([A-Z][A-Za-z0-9&,\-/]*(?:\s+[A-Z][A-Za-z0-9&,\-/]*){0,7})"?\s+refers\s+to\b'),
        ),
    ],
    "ko": [
        TermPattern("ko.quoted", re.compile(r"['\u2018\u2019\u201c\u201d\"]([\w\s]{2,40})['\u2018\u2019\u201c\u201d\"]")),
        TermPattern("ko.hereinafter", re.compile(r"이하\s+['\"\u2018\u201c]([^'\"\u2019\u201d]+)['\"\u2019\u201d]")),
    ],
    "zh-cn": [
        TermPattern("zh-cn.quoted", re.compile(r"[\u201c\u300c]([^\u201d\u300d]{2,30})[\u201d\u300d]")),
        TermPattern("zh-cn.short", re.compile(r"以下简称['\"\u201c\u300c]([^'\"\u201d\u300d]+)")),
        TermPattern("zh-cn.called", re.compile(r"以下称为['\"\u201c\u300c]([^'\"\u201d\u300d]+)")),
    ],
    "zh-tw": [
        TermPattern("zh-tw.quoted", re.compile(r"[\u201c\u300c]([^\u201d\u300d]{2,30})[\u201d\u300d]")),
        TermPattern("zh-tw.short", re.compile(r"以下簡稱['\"\u201c\u300c]([^'\"\u201d\u300d]+)")),
    ],
    "ja": [
        TermPattern("ja.quoted", re.compile(r"[\u300c\u300e]([^\u300d\u300f]{2,30})[\u300d\u300f]")),
        TermPattern("ja.hereinafter", re.compile(r"以下[「\u300c]([^」\u300d]+)[」\u300d]という")),
    ],
}


def normalize_language(lang: str) -> str:
    lang = lang.lower().strip()
    aliases = {
        "en": "en",
        "eng": "en",
        "english": "en",
        "ko": "ko",
        "kor": "ko",
        "korean": "ko",
        "zh-cn": "zh-cn",
        "zhs": "zh-cn",
        "zh_cn": "zh-cn",
        "chinese-simplified": "zh-cn",
        "zh-tw": "zh-tw",
        "zht": "zh-tw",
        "zh_tw": "zh-tw",
        "chinese-traditional": "zh-tw",
        "ja": "ja",
        "ja-jp": "ja",
        "jpn": "ja",
        "japanese": "ja",
        "ja_jp": "ja",
    }
    if lang in aliases:
        return aliases[lang]
    raise ValueError(f"Unsupported language code: {lang}. Supported: en, ko, zh-cn, zh-tw, ja")


def extract_term_hits(text: str, lang: str) -> list[TermHit]:
    lang = normalize_language(lang)
    hits: list[TermHit] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern in DEFINED_TERM_PATTERNS.get(lang, []):
            for match in pattern.regex.finditer(line):
                term = match.group(1).strip()
                if len(term) < 2 or term.isdigit():
                    continue
                hits.append(
                    TermHit(
                        term=term,
                        pattern_id=pattern.pattern_id,
                        candidate_type=pattern.candidate_type,
                        line=line_number,
                        context=line.strip(),
                    )
                )
    return hits


def unique_terms(text: str, lang: str) -> list[str]:
    return sorted({hit.term for hit in extract_term_hits(text, lang)})
