#!/usr/bin/env python3
"""sanitize.py — Ingest-time prompt-injection scanner.

Wraps every suspicious match in <escape>...</escape> and emits an audit
sidecar. Called from parse-docx.sh, parse-pdf.sh, parse-generic.sh and
from any other ingest path.

Usage:
    python3 sanitize.py <input.md> <output.md>
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # Role markers: prefer whole-element matches before open/close tags.
    ("role.xml.role_block", re.compile(r"<role(\s[^>]*)?>.*?</role>", re.I | re.S), "any"),
    ("role.chatml.close", re.compile(r"<\|/(system|user|assistant)\|>", re.I), "any"),
    ("role.chatml.open", re.compile(r"<\|(system|user|assistant)\|>", re.I), "any"),
    (
        "role.xml.close",
        re.compile(r"</(system_prompt|system|user|assistant|instructions?|role|admin|지시|시스템)>", re.I),
        "any",
    ),
    (
        "role.xml.open",
        re.compile(r"<(system_prompt|system|user|assistant|instructions?|role|admin|지시|시스템)(\s[^>]*)?>", re.I),
        "any",
    ),
    ("role.bracket.en", re.compile(r"\[(SYSTEM|USER|ASSISTANT|ADMIN|INSTRUCTION|INST)\]", re.I), "en"),
    ("role.bracket.ko", re.compile(r"\[(시스템|사용자|관리자|지시|명령)\]"), "ko"),
    ("role.firewall", re.compile(r"#{2,}\s*(SYSTEM|ADMIN|INSTRUCTION)\s*#{2,}", re.I), "any"),
    ("role.doubleangle", re.compile(r"<<\s*(system|admin|instruction|지시|시스템)\s*>>", re.I), "any"),
    # Jailbreak phrases: English.
    (
        "jailbreak.en.ignore",
        re.compile(r"\b[Ii]gnore\s+(all\s+)?previous\s+(instructions?|prompts?|rules?)\b"),
        "en",
    ),
    (
        "jailbreak.en.disregard",
        re.compile(r"\b[Dd]isregard\s+(the|all|any)\s+(system|translator|previous|prior)\s+\w+\b"),
        "en",
    ),
    ("jailbreak.en.you_are_now", re.compile(r"\b[Yy]ou\s+are\s+now\s+(in\s+)?(admin|developer|dan|root|god)\b"), "en"),
    ("jailbreak.en.forget", re.compile(r"\b[Ff]orget\s+(everything|all\s+previous)\b"), "en"),
    ("jailbreak.en.new_role", re.compile(r"\b[Ff]rom\s+now\s+on\s+you\s+(are|will be|must act)\b"), "en"),
    # Jailbreak phrases: Korean.
    ("jailbreak.ko.ignore", re.compile(r"이전\s*(의)?\s*지시(사항|들)?\s*(을|를|은|는)?\s*(모두)?\s*무시"), "ko"),
    ("jailbreak.ko.forget", re.compile(r"지금까지의?\s*(지시|규칙|프롬프트|명령)(을|를|은|는)?\s*(모두)?\s*잊"), "ko"),
    ("jailbreak.ko.you_are_now", re.compile(r"당신은\s*이제부터(는)?\s*"), "ko"),
    ("jailbreak.ko.disregard", re.compile(r"시스템\s*프롬프트(를|을)?\s*무시"), "ko"),
    # Jailbreak phrases: Chinese / Japanese.
    ("jailbreak.zh.ignore", re.compile(r"忽略(以前|之前|先前)(所有)?(的)?(指令|指示|规则|提示)"), "zh"),
    ("jailbreak.zh.you_are_now", re.compile(r"从现在开始你是"), "zh"),
    ("jailbreak.ja.ignore", re.compile(r"(これ|今)まで(の)?(指示|ルール|プロンプト)(を)?(すべて|全て)?無視"), "ja"),
    ("jailbreak.ja.you_are_now", re.compile(r"これからあなたは"), "ja"),
]

ESCAPE_OPEN = "<escape>"
ESCAPE_CLOSE = "</escape>"


@dataclass
class Hit:
    start: int
    end: int
    pattern_id: str
    match: str
    lang: str


def sanitize(text: str) -> tuple[str, list[dict]]:
    """Wrap every injection-pattern match in <escape>...</escape>."""
    hits: list[Hit] = []
    for pattern_id, regex, lang in PATTERNS:
        for match in regex.finditer(text):
            if _already_escaped(text, match.start()):
                continue
            hits.append(
                Hit(
                    start=match.start(),
                    end=match.end(),
                    pattern_id=pattern_id,
                    match=match.group(0),
                    lang=lang,
                )
            )

    if not hits:
        return text, []

    hits.sort(key=lambda hit: (hit.start, -(hit.end - hit.start)))
    resolved: list[Hit] = []
    cursor = -1
    for hit in hits:
        if hit.start >= cursor:
            resolved.append(hit)
            cursor = hit.end

    sanitized = text
    for hit in reversed(resolved):
        sanitized = (
            sanitized[: hit.start]
            + ESCAPE_OPEN
            + sanitized[hit.start : hit.end]
            + ESCAPE_CLOSE
            + sanitized[hit.end :]
        )

    audit = [_build_audit_entry(text, hit) for hit in resolved]
    return sanitized, audit


def _already_escaped(text: str, position: int) -> bool:
    open_index = text.rfind(ESCAPE_OPEN, 0, position)
    if open_index == -1:
        return False
    close_index = text.rfind(ESCAPE_CLOSE, open_index, position)
    return close_index == -1


def _build_audit_entry(text: str, hit: Hit) -> dict:
    prefix = text[: hit.start]
    line = prefix.count("\n") + 1
    column = hit.start - (prefix.rfind("\n") + 1)
    return {
        "pattern_id": hit.pattern_id,
        "match": hit.match,
        "line": line,
        "column": column,
        "lang": hit.lang,
    }


def _cli(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: sanitize.py <input> <output>", file=sys.stderr)
        return 2

    source = Path(argv[1])
    output = Path(argv[2])
    text = source.read_text(encoding="utf-8")
    sanitized, audit = sanitize(text)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(sanitized, encoding="utf-8")
    sidecar = output.with_suffix(output.suffix + ".audit.json")
    sidecar.write_text(
        json.dumps(
            {
                "source": str(source),
                "output": str(output),
                "match_count": len(audit),
                "matches": audit,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if audit:
        print(f"sanitize: {len(audit)} match(es); audit -> {sidecar}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
