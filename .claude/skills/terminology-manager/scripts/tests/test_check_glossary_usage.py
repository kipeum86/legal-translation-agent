import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check-glossary-usage.py"
SPEC = importlib.util.spec_from_file_location("check_glossary_usage", SCRIPT)
check_glossary_usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_glossary_usage)


def test_exact_target_term_passes():
    entries = [{"source_term": "Confidential Information", "target_term": "비밀정보", "origin": "llm"}]
    result = check_glossary_usage.check_usage(
        '"Confidential Information" means data.',
        "비밀정보란 데이터를 의미한다.",
        entries,
    )
    assert result["overall_status"] == "PASS"
    assert result["findings"][0]["status"] == "PASS"


def test_missing_target_term_fails():
    entries = [{"source_term": "Confidential Information", "target_term": "비밀정보", "origin": "llm"}]
    result = check_glossary_usage.check_usage(
        '"Confidential Information" means data.',
        "기밀 정보란 데이터를 의미한다.",
        entries,
    )
    assert result["overall_status"] == "FAIL"
    assert result["findings"][0]["target_status"] == "MISSING"


def test_absent_source_term_is_not_checked():
    entries = [{"source_term": "Receiving Party", "target_term": "수령당사자", "origin": "llm"}]
    result = check_glossary_usage.check_usage("No matching term.", "본문", entries)
    assert result["overall_status"] == "PASS"
    assert result["findings"][0]["status"] == "NOT_IN_SOURCE"
