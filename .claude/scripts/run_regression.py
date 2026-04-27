#!/usr/bin/env python3
"""Run the local dry-run regression gate for legal-translation-agent."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
PYTHON = sys.executable or "python3"


class RegressionFailure(RuntimeError):
    pass


def run(command: list[str], *, env: dict[str, str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        message = "\n".join(
            [
                f"Command failed ({result.returncode}): {' '.join(command)}",
                result.stdout.strip(),
                result.stderr.strip(),
            ]
        ).strip()
        raise RegressionFailure(message)
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_fixtures(private_root: Path) -> None:
    (private_root / "input").mkdir(parents=True, exist_ok=True)
    (private_root / "output" / "working").mkdir(parents=True, exist_ok=True)
    (private_root / "output" / "documents").mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURES / "docs" / "nda_en_simple.md", private_root / "input" / "nda_en_simple.md")
    shutil.copy2(FIXTURES / "docs" / "nda_ko_simple_target.md", private_root / "output" / "working" / "synthesized.md")
    shutil.copy2(FIXTURES / "glossaries" / "valid-working-glossary.json", private_root / "output" / "working" / "working-glossary.json")
    shutil.copytree(FIXTURES / "library" / "acme", private_root / "library" / "acme", dirs_exist_ok=True)
    segments = private_root / "output" / "working" / "segments" / "seg_001"
    segments.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURES / "docs" / "nda_en_simple.md", segments / "source.md")
    (segments / "pass-a.md").write_text("제1조 정의\n\n비밀정보란 비공개 정보를 의미한다.\n", encoding="utf-8")
    (segments / "pass-b.md").write_text("제1조 정의\n\n비밀정보는 비공개 정보를 의미한다.\n", encoding="utf-8")


def create_docx_fixture(path: Path) -> None:
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    def paragraph(text: str) -> str:
        return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"

    document_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{word_ns}"><w:body>'
        + paragraph("Article 1. Definitions")
        + "<w:tbl><w:tr><w:tc>"
        + paragraph("Fee")
        + "</w:tc><w:tc>"
        + paragraph("100")
        + "</w:tc></w:tr></w:tbl>"
        + f'<w:p><w:ins>{paragraph("Inserted text")}</w:ins></w:p>'
        + "</w:body></w:document>"
    )
    footnotes_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:footnotes xmlns:w="{word_ns}">'
        f'<w:footnote w:id="1">{paragraph("Footnote text")}</w:footnote>'
        "</w:footnotes>"
    )
    comments_xml = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:comments xmlns:w="{word_ns}">'
        f'<w:comment w:id="0">{paragraph("Comment text")}</w:comment>'
        "</w:comments>"
    )
    header_xml = f'<?xml version="1.0"?><w:hdr xmlns:w="{word_ns}">{paragraph("Header text")}</w:hdr>'
    footer_xml = f'<?xml version="1.0"?><w:ftr xmlns:w="{word_ns}">{paragraph("Footer text")}</w:ftr>'
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/footnotes.xml", footnotes_xml)
        package.writestr("word/comments.xml", comments_xml)
        package.writestr("word/header1.xml", header_xml)
        package.writestr("word/footer1.xml", footer_xml)


def validate(schema: str, artifact: Path, *, env: dict[str, str]) -> None:
    run([
        PYTHON,
        ".claude/scripts/validate-artifact.py",
        "--schema",
        f".claude/schemas/{schema}",
        "--file",
        str(artifact),
    ], env=env)


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionFailure(message)


def run_gate(private_root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["LEGAL_TRANSLATION_PRIVATE_DIR"] = str(private_root)
    copy_fixtures(private_root)

    report: OrderedDict[str, Any] = OrderedDict(
        [
            ("private_root", str(private_root)),
            ("checks", []),
            ("artifacts", {}),
        ]
    )

    def mark(name: str, artifact: Path | None = None) -> None:
        report["checks"].append({"name": name, "status": "PASS"})
        if artifact is not None:
            report["artifacts"][name] = str(artifact)

    job_id = "regression-normal"
    run([
        PYTHON,
        ".claude/scripts/translate-job.py",
        "start",
        "--input",
        "input/nda_en_simple.md",
        "--target",
        "ko",
        "--source-lang",
        "en",
        "--mode",
        "normal",
        "--job-id",
        job_id,
        "--dry-run",
    ], env=env)
    checkpoint = private_root / "output" / "working" / "jobs" / job_id / "checkpoint.json"
    manifest = private_root / "output" / "working" / "jobs" / job_id / "manifest.json"
    validate("checkpoint.schema.json", checkpoint, env=env)
    validate("manifest.schema.json", manifest, env=env)
    normal_manifest = load_json(manifest)
    ensure(normal_manifest["mode_plan"]["final_step"] == 7, "Normal mode must finish at Step 7")
    ensure(normal_manifest["mode_plan"]["required_model_call_count"] == 3, "Normal mode must plan Pass A/B plus synthesis")
    mark("job_start", manifest)

    mode_contracts = {"normal": normal_manifest}
    for mode, final_step, required_calls in [("fast", 5, 1), ("hard", 10, 5)]:
        mode_job_id = f"regression-{mode}"
        run([
            PYTHON,
            ".claude/scripts/translate-job.py",
            "start",
            "--input",
            "input/nda_en_simple.md",
            "--target",
            "ko",
            "--source-lang",
            "en",
            "--mode",
            mode,
            "--job-id",
            mode_job_id,
            "--dry-run",
        ], env=env)
        mode_manifest = private_root / "output" / "working" / "jobs" / mode_job_id / "manifest.json"
        validate("manifest.schema.json", mode_manifest, env=env)
        payload = load_json(mode_manifest)
        ensure(payload["mode_plan"]["final_step"] == final_step, f"{mode} mode final step mismatch")
        ensure(
            payload["mode_plan"]["required_model_call_count"] == required_calls,
            f"{mode} mode model call plan mismatch",
        )
        mode_contracts[mode] = payload
    ensure(
        mode_contracts["fast"]["mode_plan"]["artifact_count"]
        < mode_contracts["normal"]["mode_plan"]["artifact_count"]
        < mode_contracts["hard"]["mode_plan"]["artifact_count"],
        "Mode artifact counts should grow from Fast to Normal to Hard",
    )
    ensure(
        mode_contracts["hard"]["mode_plan"]["conditional_model_call_count"] == 1,
        "Hard mode should keep Library comparison conditional",
    )
    mark("mode_plan_contracts", private_root / "output" / "working" / "jobs" / "regression-hard" / "manifest.json")

    source_inventory = private_root / "output" / "working" / "structural-inventory.json"
    target_inventory = private_root / "output" / "working" / "target-structural-inventory.json"
    verification = private_root / "output" / "working" / "verification-checklist.json"
    run([
        PYTHON,
        ".claude/skills/document-analyzer/scripts/structural-counter.py",
        str(private_root / "input" / "nda_en_simple.md"),
        "en",
        str(source_inventory),
    ], env=env)
    run([
        PYTHON,
        ".claude/skills/document-analyzer/scripts/structural-counter.py",
        str(private_root / "output" / "working" / "synthesized.md"),
        "ko",
        str(target_inventory),
    ], env=env)
    run([
        PYTHON,
        ".claude/skills/structural-verifier/scripts/count-comparator.py",
        str(source_inventory),
        str(target_inventory),
        str(verification),
    ], env=env)
    validate("verification-checklist.schema.json", verification, env=env)
    ensure(load_json(verification)["overall_status"] == "PASS", "Expected structural verification PASS")
    run([
        PYTHON,
        ".claude/scripts/translate-job.py",
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "6",
        "--name",
        "structural",
        "--artifact",
        "output/working/verification-checklist.json",
        "--schema",
        ".claude/schemas/verification-checklist.schema.json",
        "--expect",
        "overall_status=PASS",
        "--record-as",
        "verification_checklist",
    ], env=env)
    mark("structural_verification", verification)

    candidates = private_root / "output" / "working" / "term-candidates.json"
    run([
        PYTHON,
        ".claude/skills/terminology-manager/scripts/extract-term-candidates.py",
        str(private_root / "input" / "nda_en_simple.md"),
        "en",
        str(candidates),
    ], env=env)
    validate("term-candidates.schema.json", candidates, env=env)
    ensure(load_json(candidates)["candidate_count"] >= 2, "Expected at least two term candidates")
    mark("term_candidates", candidates)

    glossary_usage = private_root / "output" / "working" / "glossary-usage-report.json"
    run([
        PYTHON,
        ".claude/skills/terminology-manager/scripts/check-glossary-usage.py",
        str(private_root / "input" / "nda_en_simple.md"),
        str(private_root / "output" / "working" / "synthesized.md"),
        str(private_root / "output" / "working" / "working-glossary.json"),
        str(glossary_usage),
    ], env=env)
    validate("glossary-usage-report.schema.json", glossary_usage, env=env)
    ensure(load_json(glossary_usage)["overall_status"] == "PASS", "Expected glossary usage PASS")
    run([
        PYTHON,
        ".claude/scripts/translate-job.py",
        "validate-gate",
        "--job-id",
        job_id,
        "--step",
        "7",
        "--name",
        "glossary_usage",
        "--artifact",
        "output/working/glossary-usage-report.json",
        "--schema",
        ".claude/schemas/glossary-usage-report.schema.json",
        "--expect",
        "overall_status=PASS",
        "--record-as",
        "glossary_usage_report",
    ], env=env)
    mark("glossary_usage", glossary_usage)

    run([
        PYTHON,
        ".claude/scripts/translate-job.py",
        "record-artifact",
        "--job-id",
        job_id,
        "--step",
        "5",
        "--name",
        "synthesized",
        "--path",
        "output/working/synthesized.md",
    ], env=env)
    mark("manifest_synthesized_recorded", manifest)

    context_pack = private_root / "output" / "working" / "context-packs" / "seg_001-translator.json"
    run([
        PYTHON,
        ".claude/scripts/build-context-pack.py",
        "--job-id",
        job_id,
        "--segment",
        "seg_001",
        "--role",
        "translator",
        "--target",
        "ko",
        "--output",
        "output/working/context-packs/seg_001-translator.json",
        "--library-profile",
        "acme",
    ], env=env)
    validate("context-pack.schema.json", context_pack, env=env)
    ensure(
        {item["source_term"] for item in load_json(context_pack)["glossary_subset"]} == {
            "Confidential Information",
            "Receiving Party",
        },
        "Context pack glossary subset did not match fixture source terms",
    )
    mark("context_pack", context_pack)

    cost_report = private_root / "output" / "working" / "context-cost-report.json"
    run([
        PYTHON,
        ".claude/scripts/estimate-context-cost.py",
        "--before",
        "output/working/segments/seg_001/source.md",
        "output/working/working-glossary.json",
        ".claude/agents/translator/references/language-guide-ko.md",
        "--after",
        "output/working/context-packs/seg_001-translator.json",
        "--output",
        "output/working/context-cost-report.json",
        "--label",
        "regression-fixture",
    ], env=env)
    validate("context-cost-report.schema.json", cost_report, env=env)
    ensure(load_json(cost_report)["estimated_saved_tokens"] > 0, "Expected context pack to reduce fixture token estimate")
    mark("context_cost", cost_report)

    library_report = private_root / "output" / "working" / "library-retrieval-report.json"
    run([
        PYTHON,
        ".claude/scripts/library-retrieval.py",
        "--profile",
        "acme",
        "--source",
        "input/nda_en_simple.md",
        "--source-lang",
        "en",
        "--target",
        "ko",
        "--output",
        "output/working/library-retrieval-report.json",
        "--top-k",
        "1",
    ], env=env)
    validate("library-retrieval-report.schema.json", library_report, env=env)
    ensure(load_json(library_report)["selected_count"] == 1, "Expected exactly one Library reference")
    mark("library_retrieval", library_report)

    batch_plan = private_root / "output" / "working" / "batches" / "regression-batch" / "batch-plan.json"
    batch_review = private_root / "output" / "working" / "batches" / "regression-batch" / "batch-glossary-review.json"
    run([
        PYTHON,
        ".claude/scripts/translate-batch.py",
        "start",
        "--input",
        "input",
        "--target",
        "ko",
        "--source-lang",
        "en",
        "--mode",
        "normal",
        "--job-id",
        "regression-batch",
        "--dry-run",
    ], env=env)
    validate("batch-plan.schema.json", batch_plan, env=env)
    validate("batch-glossary-review.schema.json", batch_review, env=env)
    batch_payload = load_json(batch_plan)
    review_payload = load_json(batch_review)
    ensure(batch_payload["phases"][1]["lock"] == "batch_glossary", "Expected batch glossary lock phase")
    ensure(batch_payload["phases"][2]["requires"] == ["batch-glossary-review.json approved"], "Expected Phase 3 lock dependency")
    ensure(review_payload["lock_policy"]["automatic_conflict_resolution"] is False, "Batch conflicts must not auto-resolve")
    ensure(review_payload["locks"]["defined_terms"], "Expected dry-run defined-term lock candidates")
    mark("batch_plan", batch_plan)

    docx_fixture = private_root / "input" / "tables-footnotes.docx"
    create_docx_fixture(docx_fixture)
    run([
        "bash",
        ".claude/skills/document-analyzer/scripts/parse-docx.sh",
        "input/tables-footnotes.docx",
        "output/working/docx-fixture",
    ], env=env)
    docx_structure = private_root / "output" / "working" / "docx-fixture" / "source-structure.json"
    validate("source-structure.schema.json", docx_structure, env=env)
    docx_payload = load_json(docx_structure)
    ensure(docx_payload["tables"], "Expected DOCX table extraction")
    ensure(docx_payload["footnotes"], "Expected DOCX footnote extraction")
    ensure(docx_payload["headers"], "Expected DOCX header extraction")
    ensure(docx_payload["tracked_changes_detected"], "Expected tracked changes detection")
    mark("docx_structure", docx_structure)

    pdf_parsed = private_root / "output" / "working" / "empty-pdf-text.md"
    pdf_parsed.write_text(" \f ", encoding="utf-8")
    pdf_structure = private_root / "output" / "working" / "empty-pdf-structure.json"
    run([
        PYTHON,
        ".claude/skills/document-analyzer/scripts/pdf-structure.py",
        str(private_root / "input" / "scan.pdf"),
        str(pdf_parsed),
        str(pdf_structure),
    ], env=env)
    validate("source-structure.schema.json", pdf_structure, env=env)
    ensure(load_json(pdf_structure)["ocr_required_likely"], "Expected low-density PDF OCR warning")
    mark("pdf_ocr_heuristic", pdf_structure)

    run([
        "bash",
        ".claude/skills/output-generator/scripts/file-converter.sh",
        "output/working/synthesized.md",
        "md",
        "output/documents",
        "--filename",
        "regression-final",
        "--date",
        "2026-04-27",
        "--doctype",
        "nda",
        "--src",
        "en",
        "--tgt",
        "ko",
        "--mode",
        "normal",
        "--job-id",
        job_id,
        "--step",
        "7",
    ], env=env)
    final_output = private_root / "output" / "documents" / "regression-final.md"
    provenance = Path(f"{final_output}.provenance.json")
    validate("output-provenance.schema.json", provenance, env=env)
    provenance_payload = load_json(provenance)
    ensure(provenance_payload["manifest"]["translation_source_current"], "Expected current translation source in provenance")
    ensure(provenance_payload["manifest"]["final_output_recorded"], "Expected final output to be recorded in manifest")
    forbidden = ["[SECURITY:", "[STRUCTURAL GAP:", "Quality Gate Results"]
    final_text = final_output.read_text(encoding="utf-8")
    ensure(not any(marker in final_text for marker in forbidden), "Final body contains internal marker text")
    mark("output_provenance", provenance)

    report["status"] = "PASS"
    report["check_count"] = len(report["checks"])
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local dry-run regression gate.")
    parser.add_argument("--private-dir", default=None, help="Use this LEGAL_TRANSLATION_PRIVATE_DIR instead of a temp dir")
    parser.add_argument("--report", default=None, help="Write regression report JSON here")
    parser.add_argument("--keep-private-dir", action="store_true", help="Do not delete generated temp private dir")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.private_dir:
        private_root = Path(args.private_dir).expanduser().resolve()
        private_root.mkdir(parents=True, exist_ok=True)
        should_cleanup = False
    else:
        private_root = Path(tempfile.mkdtemp(prefix="legal-translation-regression-")).resolve()
        should_cleanup = not args.keep_private_dir

    try:
        report = run_gate(private_root)
        report_path = Path(args.report).expanduser().resolve() if args.report else private_root / "regression-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Regression gate: PASS ({report['check_count']} checks) -> {report_path}")
        if args.keep_private_dir or args.private_dir:
            print(f"Private dir retained: {private_root}")
        return 0
    except RegressionFailure as exc:
        print(f"Regression gate: FAIL\n{exc}", file=sys.stderr)
        if args.keep_private_dir or args.private_dir:
            print(f"Private dir retained: {private_root}", file=sys.stderr)
        return 1
    finally:
        if should_cleanup:
            shutil.rmtree(private_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
