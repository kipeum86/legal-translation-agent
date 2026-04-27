import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import context_pack  # noqa: E402
import estimate_context_cost  # noqa: E402


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_context_pack_filters_glossary_to_segment(tmp_path, monkeypatch):
    private = tmp_path / "private"
    segment = private / "output" / "working" / "segments" / "seg_001" / "source.md"
    segment.parent.mkdir(parents=True)
    segment.write_text('"Confidential Information" means non-public data.', encoding="utf-8")
    glossary = private / "output" / "working" / "working-glossary.json"
    glossary.write_text(
        json.dumps({
            "entries": [
                {"source_term": "Confidential Information", "target_term": "비밀정보"},
                {"source_term": "Receiving Party", "target_term": "수령당사자"},
            ]
        }),
        encoding="utf-8",
    )
    inventory = private / "output" / "working" / "structural-inventory.json"
    inventory.write_text(
        json.dumps({"source_language": "en", "total_articles": 1, "articles": [], "segments": []}),
        encoding="utf-8",
    )
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    output = tmp_path / "pack.json"
    assert context_pack.main([
        "--job-id",
        "job-1",
        "--segment",
        "seg_001",
        "--role",
        "translator",
        "--target",
        "ko",
        "--output",
        str(output),
    ]) == 0

    pack = load_json(output)
    assert [item["source_term"] for item in pack["glossary_subset"]] == ["Confidential Information"]
    assert pack["source_token_estimate"] > 0
    assert pack["language_rules_subset"]


def test_estimate_context_cost_reports_reduction(tmp_path):
    before_a = tmp_path / "before-a.md"
    before_b = tmp_path / "before-b.md"
    after = tmp_path / "after.json"
    report_path = tmp_path / "report.json"
    before_a.write_text("alpha beta gamma " * 100, encoding="utf-8")
    before_b.write_text("alpha beta gamma " * 100, encoding="utf-8")
    after.write_text('{"source_span":"alpha beta gamma"}', encoding="utf-8")

    assert estimate_context_cost.main([
        "--before",
        str(before_a),
        str(before_b),
        "--after",
        str(after),
        "--output",
        str(report_path),
    ]) == 0
    report = load_json(report_path)
    assert report["total_after_tokens"] < report["total_before_tokens"]
    assert report["repeated_source_tokens"] == report["total_before_tokens"]
