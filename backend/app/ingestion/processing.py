from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_DIMENSION,
    EMBEDDING_PROVIDER,
    STORAGE_DIR,
)
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.ingestion.chunking import chunk_pages
from app.ingestion.embeddings import EmbeddingProvider, LocalSentenceTransformerProvider
from app.ingestion.parsing import parse_document


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int
    embedding: list[float]


def get_embedding_provider(provider_name: str = EMBEDDING_PROVIDER) -> EmbeddingProvider:
    if provider_name == "local":
        return LocalSentenceTransformerProvider()

    raise ValueError(f"Unsupported embedding provider '{provider_name}'.")


def generate_embedded_chunks(
    file_path: Path,
    embedding_provider: EmbeddingProvider,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[EmbeddedChunk]:
    parsed_pages = parse_document(file_path)
    chunks = chunk_pages(
        pages=parsed_pages,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    if not chunks:
        return []

    embeddings = embedding_provider.embed_texts([chunk.text for chunk in chunks])
    if len(embeddings) != len(chunks):
        raise ValueError(
            "Embedding provider returned a different number of vectors than generated chunks."
        )

    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                "Embedding dimension mismatch for chunk "
                f"{chunk.chunk_index}: expected {EMBEDDING_DIMENSION}, got {len(embedding)}."
            )

        embedded_chunks.append(
            EmbeddedChunk(
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
                embedding=embedding,
            )
        )

    return embedded_chunks


def persist_document_chunks(
    db: Session, document_id: int, embedded_chunks: list[EmbeddedChunk]
) -> int:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(
        synchronize_session=False
    )

    for chunk in embedded_chunks:
        db.add(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
                embedding=chunk.embedding,
            )
        )

    db.commit()
    return len(embedded_chunks)


def process_uploaded_document(
    db: Session,
    document_id: int,
    embedding_provider: EmbeddingProvider | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> int:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document {document_id} was not found.")

    source_path = STORAGE_DIR / document.storage_path
    if not source_path.exists():
        raise FileNotFoundError(f"Document file was not found at '{source_path}'.")

    provider = embedding_provider or get_embedding_provider()
    embedded_chunks = generate_embedded_chunks(
        file_path=source_path,
        embedding_provider=provider,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return persist_document_chunks(
        db=db,
        document_id=document.id,
        embedded_chunks=embedded_chunks,
    )
