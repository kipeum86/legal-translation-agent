import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "structural-counter.py"
SPEC = importlib.util.spec_from_file_location("structural_counter", SCRIPT)
structural_counter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(structural_counter)


def test_english_article_canonical_ids(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("Article 1. Definitions\nText\nArticle 2. Term\nText\n", encoding="utf-8")
    inventory = structural_counter.build_inventory(str(source), "en")
    assert [item["canonical_id"] for item in inventory["articles"]] == ["article:1", "article:2"]


def test_cjk_article_canonical_ids(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("第一条 定义\n内容\n第二条 义务\n内容\n", encoding="utf-8")
    inventory = structural_counter.build_inventory(str(source), "zh-cn")
    assert [item["canonical_id"] for item in inventory["articles"]] == ["article:1", "article:2"]


def test_defined_terms_and_footnotes_count(tmp_path):
    source = tmp_path / "source.md"
    source.write_text('Article 1. Definitions\n"Confidential Information" means data.[1]\n', encoding="utf-8")
    inventory = structural_counter.build_inventory(str(source), "en")
    assert inventory["defined_term_count"] == 1
    assert inventory["footnotes"] == 1
