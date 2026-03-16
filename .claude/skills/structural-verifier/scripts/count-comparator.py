#!/usr/bin/env python3
"""
count-comparator.py — Compare source and target structural inventories.

Performs 1:1 article-level comparison of structural element counts
between source and translated documents.

Usage:
    python3 count-comparator.py <source_inventory.json> <target_inventory.json> <output_path>

Output: verification-checklist.json
"""

import json
import sys
from pathlib import Path
from collections import OrderedDict


def load_inventory(path: str) -> dict:
    """Load and validate a structural inventory JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required_fields = ["total_articles", "articles", "total_sub_clauses", "defined_terms"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {path}")
    return data


def compare_articles(source_articles: list, target_articles: list) -> list[dict]:
    """Compare articles one-by-one between source and target."""
    results = []
    max_len = max(len(source_articles), len(target_articles))

    for i in range(max_len):
        src = source_articles[i] if i < len(source_articles) else None
        tgt = target_articles[i] if i < len(target_articles) else None

        if src is None:
            # Extra article in target (not in source)
            results.append({
                "article": tgt.get("id", f"Target-{i+1}"),
                "source_sub_clauses": 0,
                "target_sub_clauses": tgt.get("sub_clauses", 0),
                "sub_clause_match": False,
                "source_enumerated_items": 0,
                "target_enumerated_items": tgt.get("enumerated_items", 0),
                "enumerated_match": False,
                "status": "FAIL",
                "note": "Extra article in target — not present in source",
            })
        elif tgt is None:
            # Missing article in target
            results.append({
                "article": src.get("id", f"Source-{i+1}"),
                "source_sub_clauses": src.get("sub_clauses", 0),
                "target_sub_clauses": 0,
                "sub_clause_match": False,
                "source_enumerated_items": src.get("enumerated_items", 0),
                "target_enumerated_items": 0,
                "enumerated_match": False,
                "status": "FAIL",
                "note": "Article missing in target translation",
            })
        else:
            src_sc = src.get("sub_clauses", 0)
            tgt_sc = tgt.get("sub_clauses", 0)
            src_ei = src.get("enumerated_items", 0)
            tgt_ei = tgt.get("enumerated_items", 0)
            sc_match = src_sc == tgt_sc
            ei_match = src_ei == tgt_ei
            status = "PASS" if (sc_match and ei_match) else "FAIL"

            entry = {
                "article": src.get("id", f"Article-{i+1}"),
                "source_sub_clauses": src_sc,
                "target_sub_clauses": tgt_sc,
                "sub_clause_match": sc_match,
                "source_enumerated_items": src_ei,
                "target_enumerated_items": tgt_ei,
                "enumerated_match": ei_match,
                "status": status,
            }

            if not sc_match:
                diff = tgt_sc - src_sc
                entry["sub_clause_diff"] = diff
                entry["note"] = f"Sub-clause count mismatch: {'+' if diff > 0 else ''}{diff}"
            if not ei_match:
                diff = tgt_ei - src_ei
                entry["enumerated_diff"] = diff
                note = f"Enumerated item count mismatch: {'+' if diff > 0 else ''}{diff}"
                entry["note"] = entry.get("note", "") + ("; " if "note" in entry else "") + note

            results.append(entry)

    return results


def compare_inventories(source: dict, target: dict) -> dict:
    """Full comparison of two structural inventories."""
    # Article-level comparison
    article_results = compare_articles(
        source.get("articles", []),
        target.get("articles", []),
    )

    # Summary counts
    article_count_match = source["total_articles"] == target.get("total_articles", 0)
    sub_clause_match = source["total_sub_clauses"] == target.get("total_sub_clauses", 0)

    # Defined terms check
    source_terms = set(source.get("defined_terms", []))
    target_terms = set(target.get("defined_terms", []))
    # Note: defined terms will be in different languages, so we only compare counts
    term_count_match = len(source_terms) == len(target_terms)

    # Overall result
    all_articles_pass = all(r["status"] == "PASS" for r in article_results)
    overall_pass = all_articles_pass and article_count_match

    failed_articles = [r["article"] for r in article_results if r["status"] == "FAIL"]

    checklist = OrderedDict([
        ("source_language", source.get("source_language", "unknown")),
        ("target_language", target.get("source_language", "unknown")),
        ("overall_status", "PASS" if overall_pass else "FAIL"),
        ("summary", OrderedDict([
            ("total_articles_source", source["total_articles"]),
            ("total_articles_target", target.get("total_articles", 0)),
            ("article_count_match", article_count_match),
            ("total_sub_clauses_source", source["total_sub_clauses"]),
            ("total_sub_clauses_target", target.get("total_sub_clauses", 0)),
            ("sub_clause_count_match", sub_clause_match),
            ("defined_terms_source", len(source_terms)),
            ("defined_terms_target", len(target_terms)),
            ("defined_term_count_match", term_count_match),
            ("footnotes_source", source.get("footnotes", 0)),
            ("footnotes_target", target.get("footnotes", 0)),
        ])),
        ("failed_articles", failed_articles),
        ("article_details", article_results),
    ])

    return checklist


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 count-comparator.py <source_inventory.json> <target_inventory.json> <output_path>")
        sys.exit(1)

    source_path = sys.argv[1]
    target_path = sys.argv[2]
    output_path = sys.argv[3]

    for path in [source_path, target_path]:
        if not Path(path).exists():
            print(f"Error: File not found: {path}")
            sys.exit(1)

    try:
        source = load_inventory(source_path)
        target = load_inventory(target_path)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading inventory: {e}")
        sys.exit(1)

    checklist = compare_inventories(source, target)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    status = checklist["overall_status"]
    icon = "PASS" if status == "PASS" else "FAIL"
    print(f"Structural Verification: [{icon}]")
    print(f"  Articles: {checklist['summary']['total_articles_source']} source / {checklist['summary']['total_articles_target']} target")
    print(f"  Sub-clauses: {checklist['summary']['total_sub_clauses_source']} source / {checklist['summary']['total_sub_clauses_target']} target")
    if checklist["failed_articles"]:
        print(f"  Failed articles: {', '.join(checklist['failed_articles'])}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
