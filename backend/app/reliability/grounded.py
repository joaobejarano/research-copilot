import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.document_chunk import DocumentChunk
from app.qa.service import Citation
from app.reliability.schemas import (
    ConfidenceSignal,
    ReliabilityAssessment,
    VerificationCheckResult,
)
from app.reliability.service import ReliabilityService

NUMERIC_PATTERN = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b")
INLINE_CITATION_PATTERN = re.compile(r"\[\s*C\d+\s*]")


@dataclass(frozen=True)
class GroundedAskVerificationResult:
    assessment: ReliabilityAssessment
    unsupported_numeric_claims: list[str]


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _strip_inline_citation_markers(text: str) -> str:
    return INLINE_CITATION_PATTERN.sub("", text)


def _normalize_numeric_token(token: str) -> str:
    return token.replace(",", "")


def _extract_numeric_tokens(text: str) -> set[str]:
    normalized = _strip_inline_citation_markers(_normalize_whitespace(text))
    return {_normalize_numeric_token(match.group(0)) for match in NUMERIC_PATTERN.finditer(normalized)}


def _contains_excerpt(*, excerpt: str, chunk_text: str) -> bool:
    normalized_excerpt = _normalize_whitespace(excerpt)
    if not normalized_excerpt:
        return False

    if normalized_excerpt.endswith("..."):
        normalized_excerpt = normalized_excerpt[:-3].rstrip()

    if not normalized_excerpt:
        return False

    normalized_chunk = _normalize_whitespace(chunk_text)
    return normalized_excerpt.lower() in normalized_chunk.lower()


def _score_ratio(successes: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return successes / total


def _normalize_retrieval_score(value: float) -> float:
    normalized = (value + 1.0) / 2.0
    return max(0.0, min(1.0, normalized))


class GroundedAskReliabilityEvaluator:
    def __init__(
        self,
        *,
        reliability_service: ReliabilityService | None = None,
    ) -> None:
        self._reliability_service = reliability_service or ReliabilityService()

    def evaluate(
        self,
        *,
        db: Session,
        document_id: int,
        answer: str,
        citations: list[Citation],
    ) -> GroundedAskVerificationResult:
        chunk_map = self._load_chunks_by_index(
            db=db,
            document_id=document_id,
            chunk_indexes={citation.chunk_index for citation in citations},
        )

        checks = self._build_verification_checks(
            document_id=document_id,
            citations=citations,
            chunk_map=chunk_map,
        )
        verification = self._reliability_service.summarize_verification(checks=checks)

        unsupported_numeric_claims = self._find_unsupported_numeric_claims(
            answer=answer,
            citations=citations,
            chunk_map=chunk_map,
        )
        signals = self._build_confidence_signals(
            citations=citations,
            verification_status=verification.status,
            unsupported_numeric_claims=unsupported_numeric_claims,
        )
        confidence = self._reliability_service.score_confidence(
            signals=signals,
            verification=verification,
        )
        gate_decision = self._reliability_service.decide_gate(
            confidence=confidence,
            verification=verification,
        )

        issues = [*verification.issues]
        if unsupported_numeric_claims:
            issues.append(
                "Unsupported numeric claims detected: "
                + ", ".join(sorted(unsupported_numeric_claims))
            )

        return GroundedAskVerificationResult(
            assessment=ReliabilityAssessment(
                verification=verification,
                confidence=confidence,
                gate_decision=gate_decision,
                issues=issues,
            ),
            unsupported_numeric_claims=sorted(unsupported_numeric_claims),
        )

    def _load_chunks_by_index(
        self,
        *,
        db: Session,
        document_id: int,
        chunk_indexes: set[int],
    ) -> dict[int, DocumentChunk]:
        if not chunk_indexes:
            return {}

        chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_index.in_(sorted(chunk_indexes)),
            )
            .all()
        )
        return {chunk.chunk_index: chunk for chunk in chunks}

    def _build_verification_checks(
        self,
        *,
        document_id: int,
        citations: list[Citation],
        chunk_map: dict[int, DocumentChunk],
    ) -> list[VerificationCheckResult]:
        total = len(citations)
        if total == 0:
            return [
                VerificationCheckResult(
                    check_name="citation_exists",
                    passed=False,
                    score=0.0,
                    detail="No citations were returned by grounded answer output.",
                    citation_ids=[],
                ),
                VerificationCheckResult(
                    check_name="citation_document_match",
                    passed=False,
                    score=0.0,
                    detail="No citations to validate document ownership.",
                    citation_ids=[],
                ),
                VerificationCheckResult(
                    check_name="citation_excerpt_in_chunk",
                    passed=False,
                    score=0.0,
                    detail="No citations to validate excerpt grounding.",
                    citation_ids=[],
                ),
            ]

        existing = [citation for citation in citations if citation.chunk_index in chunk_map]
        existing_ids = [citation.citation_id for citation in existing]

        matching_document = [
            citation
            for citation in citations
            if citation.document_id == document_id and citation.chunk_index in chunk_map
        ]
        matching_document_ids = [citation.citation_id for citation in matching_document]

        grounded_excerpt = [
            citation
            for citation in citations
            if citation.chunk_index in chunk_map
            and _contains_excerpt(
                excerpt=citation.text_excerpt,
                chunk_text=chunk_map[citation.chunk_index].text,
            )
        ]
        grounded_excerpt_ids = [citation.citation_id for citation in grounded_excerpt]

        return [
            VerificationCheckResult(
                check_name="citation_exists",
                passed=len(existing) == total,
                score=_score_ratio(len(existing), total),
                detail=(
                    f"{len(existing)} of {total} citations reference chunks that exist "
                    "in stored document context."
                ),
                citation_ids=existing_ids,
            ),
            VerificationCheckResult(
                check_name="citation_document_match",
                passed=len(matching_document) == total,
                score=_score_ratio(len(matching_document), total),
                detail=(
                    f"{len(matching_document)} of {total} citations belong to document "
                    f"{document_id}."
                ),
                citation_ids=matching_document_ids,
            ),
            VerificationCheckResult(
                check_name="citation_excerpt_in_chunk",
                passed=len(grounded_excerpt) == total,
                score=_score_ratio(len(grounded_excerpt), total),
                detail=(
                    f"{len(grounded_excerpt)} of {total} citation excerpts were found in "
                    "their referenced chunks."
                ),
                citation_ids=grounded_excerpt_ids,
            ),
        ]

    def _find_unsupported_numeric_claims(
        self,
        *,
        answer: str,
        citations: list[Citation],
        chunk_map: dict[int, DocumentChunk],
    ) -> set[str]:
        answer_tokens = _extract_numeric_tokens(answer)
        if not answer_tokens:
            return set()

        cited_chunk_tokens: set[str] = set()
        for citation in citations:
            chunk = chunk_map.get(citation.chunk_index)
            if chunk is None:
                continue
            cited_chunk_tokens.update(_extract_numeric_tokens(chunk.text))

        return answer_tokens.difference(cited_chunk_tokens)

    def _build_confidence_signals(
        self,
        *,
        citations: list[Citation],
        verification_status: str,
        unsupported_numeric_claims: set[str],
    ) -> list[ConfidenceSignal]:
        citation_count = len(citations)
        citation_support_score = min(citation_count / 3.0, 1.0)

        retrieval_quality = 0.0
        if citations:
            retrieval_quality = sum(
                _normalize_retrieval_score(citation.retrieval_score)
                for citation in citations
            ) / citation_count

        verification_signal_value = 0.5
        if verification_status == "passed":
            verification_signal_value = 1.0
        elif verification_status == "failed":
            verification_signal_value = 0.0

        numeric_claim_support = 1.0 if not unsupported_numeric_claims else 0.0

        return [
            ConfidenceSignal(
                signal_name="supporting_citation_count",
                value=round(citation_support_score, 6),
                weight=0.30,
                detail=f"Citation count: {citation_count}.",
            ),
            ConfidenceSignal(
                signal_name="retrieval_score_quality",
                value=round(retrieval_quality, 6),
                weight=0.25,
                detail="Average normalized retrieval score from citations.",
            ),
            ConfidenceSignal(
                signal_name="verification_outcome",
                value=verification_signal_value,
                weight=0.30,
                detail=f"Verification status: {verification_status}.",
            ),
            ConfidenceSignal(
                signal_name="unsupported_numeric_claims",
                value=numeric_claim_support,
                weight=0.15,
                detail=(
                    "No unsupported numeric claims found."
                    if numeric_claim_support == 1.0
                    else "Answer contains numeric claims unsupported by cited chunks."
                ),
            ),
        ]
