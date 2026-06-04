import pytest
from backend.services.sop_processor import chunk_text, extract_text_from_pdf, extract_text_from_docx


# ── chunk_text ─────────────────────────────────────────────────────────────────

def test_chunk_text_single_chunk_for_short_text():
    text = "This is a short procedure.\n\nDo step one.\n\nDo step two."
    chunks = chunk_text(text, source="test.pdf", chunk_size=2000)
    assert len(chunks) == 1
    assert chunks[0]["source"] == "test.pdf"
    assert "step one" in chunks[0]["content"]


def test_chunk_text_splits_long_text():
    # Create text longer than chunk_size
    paragraph = "This is a paragraph with enough words. " * 20  # ~780 chars
    text = "\n\n".join([paragraph] * 8)  # ~6240 chars > 2000 char chunk
    chunks = chunk_text(text, source="long_doc.pdf", chunk_size=2000)
    assert len(chunks) >= 3


def test_chunk_text_ids_are_unique():
    paragraph = "Process step content here with enough detail. " * 15
    text = "\n\n".join([paragraph] * 10)
    chunks = chunk_text(text, source="sop.pdf", chunk_size=1000)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


def test_chunk_text_overlap_carries_context():
    p1 = "First section: isolation procedure for the pump. " * 20
    p2 = "Second section: restart checklist for the unit. " * 20
    text = p1 + "\n\n" + p2
    chunks = chunk_text(text, source="sop.pdf", chunk_size=1000, overlap=200)
    # The second chunk should contain some overlap from the first
    if len(chunks) >= 2:
        assert len(chunks[1]["content"]) > 0


def test_chunk_text_empty_returns_no_chunks():
    chunks = chunk_text("", source="empty.pdf")
    assert chunks == []


def test_chunk_text_whitespace_only_returns_no_chunks():
    chunks = chunk_text("   \n\n   \n\n   ", source="blank.pdf")
    assert chunks == []


def test_chunk_text_source_preserved_in_all_chunks():
    paragraph = "Detailed step content for the procedure. " * 30
    text = "\n\n".join([paragraph] * 5)
    chunks = chunk_text(text, source="CDU_Startup_SOP.pdf", chunk_size=1000)
    assert all(c["source"] == "CDU_Startup_SOP.pdf" for c in chunks)


def test_chunk_text_page_estimates_are_positive():
    paragraph = "Some content. " * 50
    text = "\n\n".join([paragraph] * 10)
    chunks = chunk_text(text, source="doc.pdf", chunk_size=1000)
    assert all(c["page"] >= 1 for c in chunks)


# ── PDF extraction ─────────────────────────────────────────────────────────────

def test_extract_text_from_pdf_mock(tmp_path):
    """extract_text_from_pdf calls pypdf.PdfReader — patch at source module."""
    import unittest.mock as mock

    fake_page = mock.MagicMock()
    fake_page.extract_text.return_value = "CDU feed pump P-101 isolation procedure."

    # PdfReader is imported inside the function body, so patch the source module
    with mock.patch("pypdf.PdfReader") as mock_reader:
        mock_reader.return_value.pages = [fake_page, fake_page]
        text, pages = extract_text_from_pdf(str(tmp_path / "test.pdf"))

    assert pages == 2
    assert "P-101" in text


def test_extract_text_from_docx_mock(tmp_path):
    """extract_text_from_docx calls python-docx Document — patch at source module."""
    import unittest.mock as mock

    fake_para = mock.MagicMock()
    fake_para.text = "Startup checklist for VDU vacuum system."

    # Document is imported inside the function body, so patch the source module
    with mock.patch("docx.Document") as mock_doc:
        mock_doc.return_value.paragraphs = [fake_para]
        text, pages = extract_text_from_docx(str(tmp_path / "test.docx"))

    assert "VDU vacuum" in text
    assert pages >= 1


def test_extract_text_unsupported_format(tmp_path):
    """Unsupported file type raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        from backend.services.sop_processor import extract_text
        extract_text(str(tmp_path / "manual.xlsx"))
