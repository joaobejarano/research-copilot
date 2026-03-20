from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.ingestion.parsing import ParsedPage, parse_document, parse_pdf_file, parse_txt_file


def test_parse_txt_file_returns_single_page_without_page_number(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("first line\nsecond line", encoding="utf-8")

    pages = parse_txt_file(file_path)

    assert pages == [ParsedPage(text="first line\nsecond line", page_number=None)]


def test_parse_pdf_file_returns_pages_with_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePdfPage:
        def __init__(self, text: str | None) -> None:
            self._text = text

        def extract_text(self) -> str | None:
            return self._text

    class FakePdfReader:
        def __init__(self, _: str) -> None:
            self.pages = [FakePdfPage("page one"), FakePdfPage(None)]

    monkeypatch.setattr("app.ingestion.parsing.PdfReader", FakePdfReader)

    pages = parse_pdf_file(Path("ignored.pdf"))

    assert pages == [
        ParsedPage(text="page one", page_number=1),
        ParsedPage(text="", page_number=2),
    ]


def test_parse_pdf_file_reads_real_pdf_pages(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with file_path.open("wb") as output_file:
        writer.write(output_file)

    pages = parse_pdf_file(file_path)

    assert len(pages) == 2
    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].text == ""
    assert pages[1].text == ""


def test_parse_document_dispatches_txt_parser(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello world", encoding="utf-8")

    pages = parse_document(file_path)

    assert pages == [ParsedPage(text="hello world", page_number=None)]


def test_parse_document_rejects_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.docx"
    file_path.write_bytes(b"content")

    with pytest.raises(ValueError, match="Unsupported document extension"):
        parse_document(file_path)
