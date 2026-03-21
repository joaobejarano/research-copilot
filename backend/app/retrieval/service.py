from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import EMBEDDING_DIMENSION, RETRIEVAL_MIN_SIMILARITY, RETRIEVAL_TOP_K
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.ingestion.processing import get_embedding_provider


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int
    similarity: float


def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(format(item, ".15g") for item in vector) + "]"


def _validate_retrieval_params(top_k: int, min_similarity: float) -> None:
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")
    if min_similarity < -1 or min_similarity > 1:
        raise ValueError("min_similarity must be between -1 and 1.")


def _validate_query_embedding(vector: list[float]) -> None:
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            "Embedding dimension mismatch for query: "
            f"expected {EMBEDDING_DIMENSION}, got {len(vector)}."
        )


def _generate_query_embedding(question: str) -> list[float]:
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be empty.")

    embedding_provider = get_embedding_provider()
    vectors = embedding_provider.embed_texts([normalized_question])
    if len(vectors) != 1:
        raise ValueError("Embedding provider must return one vector for one question.")

    query_embedding = [float(item) for item in vectors[0]]
    _validate_query_embedding(query_embedding)
    return query_embedding


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if len(vector_a) != len(vector_b):
        raise ValueError(
            "Embedding dimension mismatch between vectors: "
            f"{len(vector_a)} vs {len(vector_b)}."
        )

    dot_product = sum(left * right for left, right in zip(vector_a, vector_b, strict=True))
    norm_a = sum(item * item for item in vector_a) ** 0.5
    norm_b = sum(item * item for item in vector_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _retrieve_chunks_postgresql(
    db: Session,
    document_id: int,
    query_embedding: list[float],
    top_k: int,
    min_similarity: float,
) -> list[RetrievedChunk]:
    query_embedding_literal = _to_vector_literal(query_embedding)
    statement = text(
        """
        SELECT
            chunk_index,
            page_number,
            text,
            token_count,
            1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
        FROM document_chunks
        WHERE document_id = :document_id
          AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity
        ORDER BY embedding <=> CAST(:query_embedding AS vector) ASC, chunk_index ASC
        LIMIT :top_k
        """
    )

    rows = db.execute(
        statement,
        {
            "document_id": document_id,
            "query_embedding": query_embedding_literal,
            "min_similarity": min_similarity,
            "top_k": top_k,
        },
    ).mappings()

    return [
        RetrievedChunk(
            chunk_index=int(row["chunk_index"]),
            page_number=row["page_number"],
            text=str(row["text"]),
            token_count=int(row["token_count"]),
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]


def _retrieve_chunks_fallback(
    db: Session,
    document_id: int,
    query_embedding: list[float],
    top_k: int,
    min_similarity: float,
) -> list[RetrievedChunk]:
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    results: list[RetrievedChunk] = []
    for chunk in chunks:
        if chunk.embedding is None:
            continue

        similarity = _cosine_similarity(query_embedding, [float(item) for item in chunk.embedding])
        if similarity < min_similarity:
            continue

        results.append(
            RetrievedChunk(
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
                similarity=similarity,
            )
        )

    results.sort(key=lambda item: (-item.similarity, item.chunk_index))
    return results[:top_k]


def retrieve_relevant_chunks(
    db: Session,
    document_id: int,
    question: str,
    top_k: int = RETRIEVAL_TOP_K,
    min_similarity: float = RETRIEVAL_MIN_SIMILARITY,
) -> list[RetrievedChunk]:
    _validate_retrieval_params(top_k=top_k, min_similarity=min_similarity)

    document = db.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document {document_id} was not found.")

    query_embedding = _generate_query_embedding(question=question)

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        return _retrieve_chunks_postgresql(
            db=db,
            document_id=document_id,
            query_embedding=query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
        )

    return _retrieve_chunks_fallback(
        db=db,
        document_id=document_id,
        query_embedding=query_embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )
