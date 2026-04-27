import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "count-comparator.py"
SPEC = importlib.util.spec_from_file_location("count_comparator", SCRIPT)
count_comparator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(count_comparator)


def inventory(articles, **overrides):
    data = {
        "source_language": "en",
        "total_articles": len(articles),
        "articles": articles,
        "total_sub_clauses": sum(item.get("sub_clauses", 0) for item in articles),
        "total_enumerated_items": sum(item.get("enumerated_items", 0) for item in articles),
        "defined_terms": ["Confidential Information"],
        "footnotes": 1,
    }
    data.update(overrides)
    return data


def article(number, sub_clauses=0, enumerated_items=0):
    return {
        "id": f"Article {number}",
        "canonical_id": f"article:{number}",
        "sub_clauses": sub_clauses,
        "enumerated_items": enumerated_items,
    }


def test_matching_inventories_pass():
    source = inventory([article(1, 1, 2), article(2)])
    target = inventory([article(1, 1, 2), article(2)])
    result = count_comparator.compare_inventories(source, target)
    assert result["overall_status"] == "PASS"
    assert result["blocking_failures"] == []


def test_missing_article_fails():
    source = inventory([article(1), article(2)])
    target = inventory([article(1)])
    result = count_comparator.compare_inventories(source, target)
    assert result["overall_status"] == "FAIL"
    assert any(item["type"] == "missing_article" for item in result["blocking_failures"])


def test_reordered_articles_fail():
    source = inventory([article(1), article(2)])
    target = inventory([article(2), article(1)])
    result = count_comparator.compare_inventories(source, target)
    assert result["overall_status"] == "FAIL"
    assert any(item["type"] == "article_order_mismatch" for item in result["blocking_failures"])


def test_footnote_mismatch_fails():
    source = inventory([article(1)], footnotes=2)
    target = inventory([article(1)], footnotes=1)
    result = count_comparator.compare_inventories(source, target)
    assert result["overall_status"] == "FAIL"
    assert any(item["type"] == "footnote_count_mismatch" for item in result["blocking_failures"])


def test_defined_term_count_mismatch_fails():
    source = inventory([article(1)], defined_terms=["A", "B"])
    target = inventory([article(1)], defined_terms=["A"])
    result = count_comparator.compare_inventories(source, target)
    assert result["overall_status"] == "FAIL"
    assert any(item["type"] == "defined_term_count_mismatch" for item in result["blocking_failures"])
