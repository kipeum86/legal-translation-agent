import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from term_patterns import extract_term_hits, unique_terms  # noqa: E402


def test_extract_english_means_and_quotes():
    text = '"Confidential Information" means non-public data.\n"Receiving Party" refers to the recipient.'
    assert unique_terms(text, "en") == ["Confidential Information", "Receiving Party"]


def test_extract_korean_hereinafter():
    text = '본 계약에서 당사자 일방이 공개한 정보(이하 "비밀정보"라 한다)를 의미한다.'
    hits = extract_term_hits(text, "ko")
    assert any(hit.term == "비밀정보" for hit in hits)


def test_extract_japanese_hereinafter():
    text = "秘密情報（以下「秘密情報」という。）を保護する。"
    assert "秘密情報" in unique_terms(text, "ja")
