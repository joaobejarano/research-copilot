import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import RETRIEVAL_MIN_SIMILARITY, RETRIEVAL_TOP_K
from app.retrieval.service import RetrievedChunk, retrieve_relevant_chunks

ANSWERED_STATUS: Literal["answered"] = "answered"
INSUFFICIENT_EVIDENCE_STATUS: Literal["insufficient_evidence"] = "insufficient_evidence"
INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Insufficient evidence to answer the question from retrieved context."
)

WORD_PATTERN = re.compile(r"[a-zA-Z0-9]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "how",
}


@dataclass(frozen=True)
class Citation:
    document_id: int
    chunk_index: int
    page_number: int | None
    text_excerpt: str
    similarity: float


@dataclass(frozen=True)
class QuestionAnswerResult:
    question: str
    answer: str
    status: Literal["answered", "insufficient_evidence"]
    citations: list[Citation]


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_PATTERN.finditer(text)]


def _extract_question_keywords(question: str) -> set[str]:
    tokens = _tokenize(question)
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return []

    sentences = [item.strip() for item in SENTENCE_SPLIT_PATTERN.split(normalized) if item.strip()]
    if sentences:
        return sentences
    return [normalized]


def _excerpt(text: str, limit: int = 240) -> str:
    normalized = _normalize_whitespace(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _build_citations(document_id: int, chunks: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        citations.append(
            Citation(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text_excerpt=_excerpt(chunk.text),
                similarity=chunk.similarity,
            )
        )
    return citations


def _select_grounded_answer_sentences(
    question: str, retrieved_chunks: list[RetrievedChunk]
) -> tuple[list[str], list[RetrievedChunk]]:
    keywords = _extract_question_keywords(question)
    if not keywords:
        return [], []

    candidates: list[tuple[float, float, int, str, RetrievedChunk]] = []
    for chunk in retrieved_chunks:
        for sentence in _split_sentences(chunk.text):
            sentence_tokens = set(_tokenize(sentence))
            overlap_count = len(keywords.intersection(sentence_tokens))
            if overlap_count == 0:
                continue

            lexical_score = overlap_count / len(keywords)
            score = lexical_score + (chunk.similarity * 0.25)
            candidates.append((score, chunk.similarity, chunk.chunk_index, sentence, chunk))

    if not candidates:
        return [], []

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))

    selected_sentences: list[str] = []
    selected_chunks: list[RetrievedChunk] = []
    seen_chunk_indexes: set[int] = set()

    for _, _, _, sentence, chunk in candidates:
        if chunk.chunk_index in seen_chunk_indexes:
            continue
        selected_sentences.append(sentence)
        selected_chunks.append(chunk)
        seen_chunk_indexes.add(chunk.chunk_index)
        if len(selected_sentences) == 2:
            break

    return selected_sentences, selected_chunks


def answer_document_question(
    db: Session,
    document_id: int,
    question: str,
    top_k: int = RETRIEVAL_TOP_K,
    min_similarity: float = RETRIEVAL_MIN_SIMILARITY,
) -> QuestionAnswerResult:
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be empty.")

    retrieved_chunks = retrieve_relevant_chunks(
        db=db,
        document_id=document_id,
        question=normalized_question,
        top_k=top_k,
        min_similarity=min_similarity,
    )

    if not retrieved_chunks:
        return QuestionAnswerResult(
            question=normalized_question,
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            status=INSUFFICIENT_EVIDENCE_STATUS,
            citations=[],
        )

    answer_sentences, answer_chunks = _select_grounded_answer_sentences(
        question=normalized_question,
        retrieved_chunks=retrieved_chunks,
    )

    if not answer_sentences:
        return QuestionAnswerResult(
            question=normalized_question,
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            status=INSUFFICIENT_EVIDENCE_STATUS,
            citations=_build_citations(document_id=document_id, chunks=retrieved_chunks[:3]),
        )

    return QuestionAnswerResult(
        question=normalized_question,
        answer=" ".join(answer_sentences),
        status=ANSWERED_STATUS,
        citations=_build_citations(document_id=document_id, chunks=answer_chunks),
    )
