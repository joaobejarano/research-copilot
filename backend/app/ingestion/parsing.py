from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedPage:
    text: str
    page_number: int | None


def parse_txt_file(file_path: Path) -> list[ParsedPage]:
    text = file_path.read_text(encoding="utf-8")
    return [ParsedPage(text=text, page_number=None)]


def parse_pdf_file(file_path: Path) -> list[ParsedPage]:
    reader = PdfReader(str(file_path))
    pages: list[ParsedPage] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(ParsedPage(text=page_text, page_number=page_number))

    return pages


def parse_document(file_path: Path) -> list[ParsedPage]:
    extension = file_path.suffix.lower()

    if extension == ".txt":
        return parse_txt_file(file_path)
    if extension == ".pdf":
        return parse_pdf_file(file_path)

    raise ValueError(f"Unsupported document extension '{extension or 'none'}'.")
