import re
from dataclasses import dataclass

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE
from app.ingestion.parsing import ParsedPage

TOKEN_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int


def approximate_token_count(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))


def _validate_chunking_params(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size.")


def chunk_pages(
    pages: list[ParsedPage],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    _validate_chunking_params(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    step = chunk_size - chunk_overlap
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        tokens = TOKEN_PATTERN.findall(page.text)
        if not tokens:
            continue

        for start in range(0, len(tokens), step):
            chunk_tokens = tokens[start : start + chunk_size]
            if not chunk_tokens:
                continue

            chunk_text = " ".join(chunk_tokens)
            chunks.append(
                Chunk(
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    text=chunk_text,
                    token_count=approximate_token_count(chunk_text),
                )
            )
            chunk_index += 1

    return chunks
