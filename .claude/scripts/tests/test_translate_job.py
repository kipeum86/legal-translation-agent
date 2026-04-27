import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import translate_job  # noqa: E402


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_start_status_resume_dry_run(tmp_path, monkeypatch, capsys):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "test-job"
    assert translate_job.main([
        "start",
        "--input",
        "input/source.md",
        "--target",
        "ko",
        "--source-lang",
        "en",
        "--job-id",
        job_id,
        "--dry-run",
    ]) == 0

    assert (private / "output" / "working" / "jobs" / job_id / "checkpoint.json").exists()
    assert (private / "output" / "working" / "jobs" / job_id / "manifest.json").exists()
    assert translate_job.main(["status", "--job-id", job_id]) == 0
    assert translate_job.main(["resume", "--job-id", job_id, "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Job created: test-job" in output
    assert "manifest checksums verified" in output


def test_start_missing_input_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(tmp_path))
    assert translate_job.main(["start", "--input", "input/missing.md", "--target", "ko"]) == 1


def test_fast_mode_manifest_uses_short_pipeline(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "fast-job"
    assert translate_job.main([
        "start",
        "--input",
        "input/source.md",
        "--target",
        "ko",
        "--mode",
        "fast",
        "--job-id",
        job_id,
    ]) == 0
    manifest = load_json(private / "output" / "working" / "jobs" / job_id / "manifest.json")
    assert [item["name"] for item in manifest["steps"]] == [
        "Document Ingestion & Analysis",
        "Terminology Extraction & Glossary Setup",
        "Single Translation Draft",
        "Structural & Glossary Verification",
        "Draft Output Assembly",
    ]
    assert manifest["mode_plan"]["draft_only"] is True
    assert manifest["mode_plan"]["required_model_call_count"] == 1
    assert manifest["mode_plan"]["model_call_plan"][0]["strategy"] == "fast-draft"


def test_mode_plan_distinguishes_fast_normal_and_hard(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    manifests = {}
    for mode in ("fast", "normal", "hard"):
        job_id = f"{mode}-contract-job"
        assert translate_job.main([
            "start",
            "--input",
            "input/source.md",
            "--target",
            "ko",
            "--mode",
            mode,
            "--job-id",
            job_id,
            "--dry-run",
        ]) == 0
        manifests[mode] = load_json(private / "output" / "working" / "jobs" / job_id / "manifest.json")

    fast_plan = manifests["fast"]["mode_plan"]
    normal_plan = manifests["normal"]["mode_plan"]
    hard_plan = manifests["hard"]["mode_plan"]

    assert fast_plan["final_step"] == 5
    assert normal_plan["final_step"] == 7
    assert hard_plan["final_step"] == 10
    assert fast_plan["artifact_count"] < normal_plan["artifact_count"] < hard_plan["artifact_count"]
    assert fast_plan["required_model_call_count"] < normal_plan["required_model_call_count"] < hard_plan["required_model_call_count"]
    assert hard_plan["conditional_model_call_count"] == 1

    normal_strategies = [item["strategy"] for item in normal_plan["model_call_plan"]]
    assert normal_strategies == [
        "source-faithful",
        "target-drafting",
        "source-and-glossary-grounded-synthesis",
    ]

    hard_step_names = [item["name"] for item in manifests["hard"]["steps"]]
    assert "Back-Translation Verification" in hard_step_names
    assert "Library Reference Comparison" in hard_step_names
    assert "Editorial Polish & Final Quality Gate" in hard_step_names

    legacy_manifest = dict(manifests["normal"])
    legacy_manifest.pop("mode_plan")
    assert translate_job.validate_manifest(legacy_manifest) == []


def test_record_artifact_updates_checkpoint_and_manifest(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    artifact = private / "output" / "working" / "term-candidates.json"
    schema = tmp_path / "artifact.schema.json"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    artifact.write_text('{"status":"PASS"}', encoding="utf-8")
    schema.write_text(
        '{"type":"object","required":["status"],"properties":{"status":{"type":"string"}}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "artifact-job"
    assert translate_job.main(["start", "--input", "input/source.md", "--target", "ko", "--job-id", job_id]) == 0
    assert translate_job.main([
        "record-artifact",
        "--job-id",
        job_id,
        "--step",
        "2",
        "--name",
        "term_candidates",
        "--path",
        "output/working/term-candidates.json",
        "--schema",
        str(schema),
        "--complete-step",
    ]) == 0

    job_root = private / "output" / "working" / "jobs" / job_id
    checkpoint = load_json(job_root / "checkpoint.json")
    manifest = load_json(job_root / "manifest.json")
    assert checkpoint["artifacts"]["term_candidates"] == str(artifact.resolve())
    assert checkpoint["last_completed_step"] == 2
    assert any(item["name"] == "term_candidates" for item in manifest["artifacts"])


def test_record_failure_tracks_retry_state(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "failure-job"
    assert translate_job.main([
        "start",
        "--input",
        "input/source.md",
        "--target",
        "ko",
        "--job-id",
        job_id,
        "--retry-budget",
        "1",
    ]) == 0
    assert translate_job.main(["record-failure", "--job-id", job_id, "--reason", "glossary usage failed"]) == 0
    checkpoint_path = private / "output" / "working" / "jobs" / job_id / "checkpoint.json"
    checkpoint = load_json(checkpoint_path)
    assert checkpoint["retry_count"] == 1
    assert checkpoint["status"] == "paused"
    assert checkpoint["failure_reason"] == "glossary usage failed"

    assert translate_job.main(["record-failure", "--job-id", job_id, "--reason", "retry failed"]) == 0
    checkpoint = load_json(checkpoint_path)
    assert checkpoint["retry_count"] == 2
    assert checkpoint["status"] == "failed"


def test_validate_gate_warn_policy_records_warning_without_blocking(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    artifact = private / "output" / "working" / "verification.json"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    artifact.write_text('{"overall_status":"FAIL"}', encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "warn-job"
    assert translate_job.main(["start", "--input", "input/source.md", "--target", "ko", "--job-id", job_id]) == 0
    assert translate_job.main([
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "6",
        "--name",
        "structural",
        "--artifact",
        "output/working/verification.json",
        "--expect",
        "overall_status=PASS",
    ]) == 0

    root = private / "output" / "working" / "jobs" / job_id
    checkpoint = load_json(root / "checkpoint.json")
    manifest = load_json(root / "manifest.json")
    assert checkpoint["status"] == "in_progress"
    assert checkpoint["validation_warnings"][0]["status"] == "WARN"
    assert manifest["validation_events"][0]["status"] == "WARN"


def test_validate_gate_enforce_new_jobs_blocks_new_job(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    artifact = private / "output" / "working" / "verification.json"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    artifact.write_text('{"overall_status":"FAIL"}', encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "enforced-job"
    assert translate_job.main([
        "start",
        "--input",
        "input/source.md",
        "--target",
        "ko",
        "--job-id",
        job_id,
        "--validation-policy",
        "enforce-new-jobs",
    ]) == 0
    assert translate_job.main([
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "6",
        "--name",
        "structural",
        "--artifact",
        "output/working/verification.json",
        "--expect",
        "overall_status=PASS",
    ]) == 1

    checkpoint = load_json(private / "output" / "working" / "jobs" / job_id / "checkpoint.json")
    assert checkpoint["status"] == "paused"
    assert checkpoint["failure_reason"] == "validation failed: structural"


def test_validate_gate_enforce_new_jobs_warns_for_legacy_warn_job(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    artifact = private / "output" / "working" / "verification.json"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    artifact.write_text('{"overall_status":"FAIL"}', encoding="utf-8")
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "legacy-job"
    assert translate_job.main(["start", "--input", "input/source.md", "--target", "ko", "--job-id", job_id]) == 0
    assert translate_job.main([
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "6",
        "--name",
        "structural",
        "--artifact",
        "output/working/verification.json",
        "--expect",
        "overall_status=PASS",
        "--validation-policy",
        "enforce-new-jobs",
    ]) == 0
    checkpoint = load_json(private / "output" / "working" / "jobs" / job_id / "checkpoint.json")
    assert checkpoint["status"] == "in_progress"
    assert checkpoint["validation_warnings"][0]["policy"] == "enforce-new-jobs"


def test_validate_gate_pass_records_artifact_and_completes_step(tmp_path, monkeypatch):
    private = tmp_path / "private"
    source = private / "input" / "source.md"
    artifact = private / "output" / "working" / "verification.json"
    schema = tmp_path / "verification.schema.json"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("Article 1. Text", encoding="utf-8")
    artifact.write_text('{"overall_status":"PASS"}', encoding="utf-8")
    schema.write_text(
        '{"type":"object","required":["overall_status"],"properties":{"overall_status":{"type":"string"}}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LEGAL_TRANSLATION_PRIVATE_DIR", str(private))

    job_id = "gate-pass-job"
    assert translate_job.main(["start", "--input", "input/source.md", "--target", "ko", "--job-id", job_id]) == 0
    assert translate_job.main([
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "6",
        "--name",
        "structural",
        "--artifact",
        "output/working/verification.json",
        "--schema",
        str(schema),
        "--expect",
        "overall_status=PASS",
        "--record-as",
        "verification_checklist",
        "--complete-step",
    ]) == 0

    root = private / "output" / "working" / "jobs" / job_id
    checkpoint = load_json(root / "checkpoint.json")
    manifest = load_json(root / "manifest.json")
    assert checkpoint["last_completed_step"] == 6
    assert checkpoint["artifacts"]["verification_checklist"] == str(artifact.resolve())
    assert any(item["name"] == "verification_checklist" for item in manifest["artifacts"])
    assert manifest["validation_events"][0]["status"] == "PASS"
