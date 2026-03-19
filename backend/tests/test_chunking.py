import pytest

from app.ingestion.chunking import Chunk, approximate_token_count, chunk_pages
from app.ingestion.parsing import ParsedPage


def test_approximate_token_count_counts_non_whitespace_tokens() -> None:
    assert approximate_token_count("alpha beta\ngamma") == 3


def test_chunk_pages_respects_chunk_size_overlap_and_page_number() -> None:
    pages = [ParsedPage(text="one two three four five six", page_number=3)]

    chunks = chunk_pages(pages=pages, chunk_size=4, chunk_overlap=1)

    assert chunks == [
        Chunk(chunk_index=0, page_number=3, text="one two three four", token_count=4),
        Chunk(chunk_index=1, page_number=3, text="four five six", token_count=3),
    ]


def test_chunk_pages_keeps_deterministic_order_across_pages() -> None:
    pages = [
        ParsedPage(text="alpha beta gamma", page_number=1),
        ParsedPage(text="", page_number=2),
        ParsedPage(text="delta epsilon", page_number=3),
    ]

    chunks = chunk_pages(pages=pages, chunk_size=2, chunk_overlap=0)

    assert chunks == [
        Chunk(chunk_index=0, page_number=1, text="alpha beta", token_count=2),
        Chunk(chunk_index=1, page_number=1, text="gamma", token_count=1),
        Chunk(chunk_index=2, page_number=3, text="delta epsilon", token_count=2),
    ]


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [
        (0, 0),
        (-1, 0),
        (2, -1),
        (2, 2),
        (2, 3),
    ],
)
def test_chunk_pages_validates_chunking_parameters(
    chunk_size: int, chunk_overlap: int
) -> None:
    with pytest.raises(ValueError):
        chunk_pages(
            pages=[ParsedPage(text="alpha beta", page_number=1)],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
