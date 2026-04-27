"""Shared text matching helpers for glossary and context-pack checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    present: bool
    match_type: str


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\s\"'“”‘’「」『』()（）.,;:，。；：]+", "", text)
    return text


def contains_exact(haystack: str, needle: str) -> bool:
    return bool(needle) and needle in haystack


def contains_normalized(haystack: str, needle: str) -> bool:
    return bool(needle) and normalize_text(needle) in normalize_text(haystack)


def match_term(haystack: str, needle: str) -> MatchResult:
    if contains_exact(haystack, needle):
        return MatchResult(True, "EXACT")
    if contains_normalized(haystack, needle):
        return MatchResult(True, "NORMALIZED")
    return MatchResult(False, "MISSING")
