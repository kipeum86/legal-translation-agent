import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

import translate_job  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "write_output_provenance.py"
SPEC = importlib.util.spec_from_file_location("write_output_provenance", SCRIPT)
write_output_provenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(write_output_provenance)


def test_output_provenance_checks_manifest_freshness(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    translation = private / "output" / "working" / "synthesized.md"
    final = private / "output" / "documents" / "final.md"
    provenance = private / "output" / "documents" / "final.md.provenance.json"
    source.parent.mkdir(parents=True)
    translation.parent.mkdir(parents=True)
    final.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    translation.write_text("제1조 본문", encoding="utf-8")
    final.write_text("제1조 본문", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    assert translate_job.main(["start", "--input", "input/source.md", "--target", "ko", "--job-id", "job-1"]) == 0
    assert translate_job.main([
        "record-artifact",
        "--job-id",
        "job-1",
        "--step",
        "7",
        "--name",
        "synthesized",
        "--path",
        str(translation),
    ]) == 0

    assert write_output_provenance.main([
        "--translation",
        str(translation),
        "--output",
        str(final),
        "--provenance",
        str(provenance),
        "--format",
        "md",
        "--mode",
        "normal",
        "--job-id",
        "job-1",
    ]) == 0

    payload = json.loads(provenance.read_text(encoding="utf-8"))
    assert payload["manifest"]["available"] is True
    assert payload["manifest"]["translation_source_current"] is True
    assert payload["manifest"]["final_output_recorded"] is False
    assert payload["appendix_policy"]["security_findings_inline"] is False
