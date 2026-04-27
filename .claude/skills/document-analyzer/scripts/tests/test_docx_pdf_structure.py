import importlib.util
import json
import zipfile
from pathlib import Path


DOCX_SCRIPT = Path(__file__).resolve().parents[1] / "docx-extract.py"
DOCX_SPEC = importlib.util.spec_from_file_location("docx_extract", DOCX_SCRIPT)
docx_extract = importlib.util.module_from_spec(DOCX_SPEC)
DOCX_SPEC.loader.exec_module(docx_extract)

PDF_SCRIPT = Path(__file__).resolve().parents[1] / "pdf-structure.py"
PDF_SPEC = importlib.util.spec_from_file_location("pdf_structure", PDF_SCRIPT)
pdf_structure = importlib.util.module_from_spec(PDF_SPEC)
PDF_SPEC.loader.exec_module(pdf_structure)


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def xml(body):
    return f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'


def p(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def test_docx_extracts_tables_headers_footnotes_comments_and_tracked_changes(tmp_path):
    docx_path = tmp_path / "fixture.docx"
    md_path = tmp_path / "source-parsed.md"
    structure_path = tmp_path / "source-structure.json"
    document_xml = xml(
        p("Article 1. Definitions")
        + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Fee</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>100</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        + '<w:p><w:ins><w:r><w:t>Inserted text</w:t></w:r></w:ins></w:p>'
    )
    footnotes_xml = f'<?xml version="1.0"?><w:footnotes xmlns:w="{W}"><w:footnote w:id="1">{p("Footnote text")}</w:footnote></w:footnotes>'
    comments_xml = f'<?xml version="1.0"?><w:comments xmlns:w="{W}"><w:comment w:id="0">{p("Comment text")}</w:comment></w:comments>'
    header_xml = f'<?xml version="1.0"?><w:hdr xmlns:w="{W}">{p("Header text")}</w:hdr>'
    footer_xml = f'<?xml version="1.0"?><w:ftr xmlns:w="{W}">{p("Footer text")}</w:ftr>'
    with zipfile.ZipFile(docx_path, "w") as package:
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/footnotes.xml", footnotes_xml)
        package.writestr("word/comments.xml", comments_xml)
        package.writestr("word/header1.xml", header_xml)
        package.writestr("word/footer1.xml", footer_xml)

    structure = docx_extract.extract(docx_path, md_path, structure_path)
    markdown = md_path.read_text(encoding="utf-8")

    assert "| Fee | 100 |" in markdown
    assert structure["tables"][0]["rows"] == [["Fee", "100"]]
    assert structure["headers"][0]["text"] == "Header text"
    assert structure["footers"][0]["text"] == "Footer text"
    assert structure["footnotes"][0]["text"] == "Footnote text"
    assert structure["comments"][0]["text"] == "Comment text"
    assert structure["tracked_changes_detected"] is True
    assert "comments_detected_not_merged" in structure["extraction_warnings"]
    assert json.loads(structure_path.read_text(encoding="utf-8"))["format"] == "docx"


def test_pdf_structure_flags_low_density_for_ocr(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    parsed_path = tmp_path / "source-parsed.md"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    parsed_path.write_text("   \f", encoding="utf-8")

    structure = pdf_structure.build_structure(pdf_path, parsed_path)

    assert structure["format"] == "pdf"
    assert structure["ocr_required_likely"] is True
    assert "ocr_required_likely" in structure["extraction_warnings"]
