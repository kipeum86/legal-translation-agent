import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_regression  # noqa: E402


def test_run_regression_gate_passes_with_fixture_private_dir(tmp_path):
    private = tmp_path / "private"
    report = tmp_path / "regression-report.json"

    assert run_regression.main([
        "--private-dir",
        str(private),
        "--report",
        str(report),
    ]) == 0

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["check_count"] >= 12
    assert (private / "output" / "documents" / "regression-final.md.provenance.json").exists()
