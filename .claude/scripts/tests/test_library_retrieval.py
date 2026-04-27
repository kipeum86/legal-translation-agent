import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import library_retrieval  # noqa: E402


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_library_retrieval_selects_top_k_and_writes_index(tmp_path, monkeypatch):
    private = tmp_path / "private"
    current = private / "input" / "source.md"
    source_ref = private / "library" / "acme" / "references" / "en-ko" / "source"
    target_ref = private / "library" / "acme" / "references" / "en-ko" / "target"
    current.parent.mkdir(parents=True)
    source_ref.mkdir(parents=True)
    target_ref.mkdir(parents=True)
    current.write_text('"Confidential Information" means data.', encoding="utf-8")
    (source_ref / "nda.md").write_text('"Confidential Information" means protected data.', encoding="utf-8")
    (target_ref / "nda.md").write_text("비밀정보란 보호 대상 정보를 의미한다.", encoding="utf-8")
    (source_ref / "misc.md").write_text('"Receiving Party" means recipient.', encoding="utf-8")
    (target_ref / "misc.md").write_text("수령당사자란 수령인을 의미한다.", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    output = tmp_path / "retrieval.json"
    assert library_retrieval.main([
        "--profile",
        "acme",
        "--source",
        "input/source.md",
        "--source-lang",
        "en",
        "--target",
        "ko",
        "--output",
        str(output),
        "--top-k",
        "1",
    ]) == 0

    report = load_json(output)
    assert report["status"] == "PASS"
    assert report["selected_count"] == 1
    assert report["selected_references"][0]["section_id"] == "nda"
    assert (private / "library" / "acme" / ".index" / "references.jsonl").exists()


def test_library_retrieval_skips_when_no_references(tmp_path, monkeypatch):
    private = tmp_path / "private"
    current = private / "input" / "source.md"
    current.parent.mkdir(parents=True)
    current.write_text("Article 1. Text", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    output = tmp_path / "retrieval.json"
    assert library_retrieval.main([
        "--profile",
        "empty",
        "--source",
        "input/source.md",
        "--source-lang",
        "en",
        "--target",
        "ko",
        "--output",
        str(output),
    ]) == 0
    assert load_json(output)["status"] == "SKIPPED"
