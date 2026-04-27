import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import translate_batch  # noqa: E402


def test_translate_batch_dry_run_writes_parallel_plan(tmp_path, monkeypatch):
    private = tmp_path / "private"
    input_dir = private / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "one.md").write_text('"Confidential Information" means non-public information.\nACME Corp. is a party.', encoding="utf-8")
    (input_dir / "two.txt").write_text('"Confidential Information" refers to protected material.', encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))
    monkeypatch.setattr(translate_batch.os, "cpu_count", lambda: 8)

    assert translate_batch.main([
        "start",
        "--input",
        "input",
        "--target",
        "ko",
        "--source-lang",
        "en",
        "--job-id",
        "batch-1",
        "--dry-run",
    ]) == 0

    plan_path = private / "output" / "working" / "batches" / "batch-1" / "batch-plan.json"
    review_path = plan_path.parent / "batch-glossary-review.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert plan["document_count"] == 2
    assert plan["concurrency"]["local_scripts"] == 4
    assert plan["concurrency"]["llm"] == 2
    assert plan["lock_policy"]["automatic_conflict_resolution"] is False
    assert plan["phases"][0]["parallelizable"] is True
    assert plan["phases"][1]["lock"] == "batch_glossary"
    assert plan["phases"][2]["requires"] == ["batch-glossary-review.json approved"]
    assert plan["phases"][2]["tasks"][0]["requires_approved_locks"] == ["defined_terms", "party_names"]

    assert review_path.exists()
    assert review["status"] == "pending_user_review"
    assert review["lock_policy"]["automatic_conflict_resolution"] is False
    assert review["requires_lock_approval"] is True
    assert review["locks"]["defined_terms"][0]["source_term"] == "Confidential Information"
    assert review["locks"]["defined_terms"][0]["doc_ids"] == ["doc-001-one", "doc-002-two"]
    assert review["locks"]["party_names"][0]["source_term"] == "ACME Corp"


def test_translate_batch_records_parser_deferred_lock_extraction(tmp_path, monkeypatch):
    private = tmp_path / "private"
    input_dir = private / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "one.pdf").write_text("placeholder", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    assert translate_batch.main([
        "start",
        "--input",
        "input",
        "--target",
        "ko",
        "--source-lang",
        "en",
        "--job-id",
        "batch-pdf",
        "--dry-run",
    ]) == 0

    review_path = private / "output" / "working" / "batches" / "batch-pdf" / "batch-glossary-review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["status"] == "ready"
    assert review["locks"]["defined_terms"] == []
    assert review["requires_lock_approval"] is False
    assert "after parser output" in review["extraction_notes"][0]["message"]
