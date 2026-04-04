from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.config import (
    MAX_WORKFLOW_CITATIONS,
    MAX_WORKFLOW_ITEMS,
    RETRIEVAL_MIN_SIMILARITY,
    RETRIEVAL_TOP_K,
)
from app.retrieval.service import RetrievedChunk, retrieve_relevant_chunks
from app.workflows.llm import StructuredLLMProvider, get_llm_provider
from app.workflows.schemas import (
    KPIDraft,
    KPIExtractionOutput,
    KPIExtractionRequest,
    MemoDraft,
    MemoGenerationOutput,
    MemoGenerationRequest,
    RiskDraft,
    RiskExtractionOutput,
    RiskExtractionRequest,
    TimelineBuildingOutput,
    TimelineBuildingRequest,
    TimelineDraft,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_GENERATED,
    WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE,
    WorkflowCitation,
    WorkflowEvidence,
)

INSUFFICIENT_EVIDENCE_INSTRUCTION = (
    "No chunks were retrieved with sufficient similarity to support a structured workflow output."
)


@dataclass(frozen=True)
class WorkflowExecutionContext:
    document_id: int
    instruction: str
    evidence: WorkflowEvidence
    prompt_context: str


class StructuredWorkflowService:
    def __init__(
        self,
        *,
        llm_provider: StructuredLLMProvider | None = None,
        max_workflow_citations: int = MAX_WORKFLOW_CITATIONS,
        max_workflow_items: int = MAX_WORKFLOW_ITEMS,
    ) -> None:
        if max_workflow_citations <= 0:
            raise ValueError("max_workflow_citations must be greater than 0.")
        if max_workflow_items <= 0:
            raise ValueError("max_workflow_items must be greater than 0.")

        self._llm_provider = llm_provider or get_llm_provider()
        self.max_workflow_citations = max_workflow_citations
        self.max_workflow_items = max_workflow_items

    # ------------------------------------------------------------------ #
    # Public high-level workflow methods                                   #
    # ------------------------------------------------------------------ #

    def generate_memo(
        self,
        *,
        db: Session,
        request: MemoGenerationRequest,
    ) -> MemoGenerationOutput:
        context = self.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
        return self._execute_memo(context)

    def extract_kpis(
        self,
        *,
        db: Session,
        request: KPIExtractionRequest,
    ) -> KPIExtractionOutput:
        context = self.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
        return self._execute_kpis(context)

    def extract_risks(
        self,
        *,
        db: Session,
        request: RiskExtractionRequest,
    ) -> RiskExtractionOutput:
        context = self.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
        return self._execute_risks(context)

    def build_timeline(
        self,
        *,
        db: Session,
        request: TimelineBuildingRequest,
    ) -> TimelineBuildingOutput:
        context = self.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
        return self._execute_timeline(context)

    # ------------------------------------------------------------------ #
    # Two-phase API: context retrieval + generation (used by streaming)    #
    # ------------------------------------------------------------------ #

    def build_context(
        self,
        *,
        db: Session,
        document_id: int,
        instruction: str,
        top_k: int | None,
        min_similarity: float | None,
    ) -> WorkflowExecutionContext:
        retrieval_top_k = top_k if top_k is not None else max(RETRIEVAL_TOP_K, self.max_workflow_citations)
        retrieval_min_similarity = (
            min_similarity if min_similarity is not None else RETRIEVAL_MIN_SIMILARITY
        )

        retrieved_chunks = retrieve_relevant_chunks(
            db=db,
            document_id=document_id,
            question=instruction,
            top_k=retrieval_top_k,
            min_similarity=retrieval_min_similarity,
        )
        evidence = self._build_evidence(document_id=document_id, chunks=retrieved_chunks)
        prompt_context = self._format_prompt_context(evidence=evidence)

        return WorkflowExecutionContext(
            document_id=document_id,
            instruction=instruction,
            evidence=evidence,
            prompt_context=prompt_context,
        )

    def _execute_memo(self, context: WorkflowExecutionContext) -> MemoGenerationOutput:
        if not context.evidence.citations:
            return MemoGenerationOutput(
                document_id=context.document_id,
                status=WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE,
                evidence=context.evidence,
            )

        draft = self._llm_provider.generate_structured_output(
            system_prompt=self._build_system_prompt("memo generation"),
            user_prompt=self._build_user_prompt(context=context),
            response_model=MemoDraft,
        )
        self._validate_citation_ids(
            citation_ids=self._memo_citation_ids(draft),
            evidence=context.evidence,
        )

        return MemoGenerationOutput(
            document_id=context.document_id,
            status=WORKFLOW_STATUS_GENERATED,
            memo=draft,
            evidence=context.evidence,
        )

    def _execute_kpis(self, context: WorkflowExecutionContext) -> KPIExtractionOutput:
        if not context.evidence.citations:
            return KPIExtractionOutput(
                document_id=context.document_id,
                status=WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE,
                evidence=context.evidence,
            )

        draft = self._llm_provider.generate_structured_output(
            system_prompt=self._build_system_prompt("kpi extraction"),
            user_prompt=self._build_user_prompt(context=context),
            response_model=KPIDraft,
        )
        self._validate_citation_ids(
            citation_ids=[kpi.citation for kpi in draft.kpis],
            evidence=context.evidence,
        )

        return KPIExtractionOutput(
            document_id=context.document_id,
            status=WORKFLOW_STATUS_COMPLETED,
            kpis=draft.kpis,
            evidence=context.evidence,
        )

    def _execute_risks(self, context: WorkflowExecutionContext) -> RiskExtractionOutput:
        if not context.evidence.citations:
            return RiskExtractionOutput(
                document_id=context.document_id,
                status=WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE,
                evidence=context.evidence,
            )

        draft = self._llm_provider.generate_structured_output(
            system_prompt=self._build_system_prompt("risk extraction"),
            user_prompt=self._build_user_prompt(context=context),
            response_model=RiskDraft,
        )
        self._validate_citation_ids(
            citation_ids=[risk.citation for risk in draft.risks],
            evidence=context.evidence,
        )

        return RiskExtractionOutput(
            document_id=context.document_id,
            status=WORKFLOW_STATUS_COMPLETED,
            risks=draft.risks,
            evidence=context.evidence,
        )

    def _execute_timeline(self, context: WorkflowExecutionContext) -> TimelineBuildingOutput:
        if not context.evidence.citations:
            return TimelineBuildingOutput(
                document_id=context.document_id,
                status=WORKFLOW_STATUS_INSUFFICIENT_EVIDENCE,
                evidence=context.evidence,
            )

        draft = self._llm_provider.generate_structured_output(
            system_prompt=self._build_system_prompt("timeline building"),
            user_prompt=self._build_user_prompt(context=context),
            response_model=TimelineDraft,
        )
        self._validate_citation_ids(
            citation_ids=[event.citation for event in draft.events],
            evidence=context.evidence,
        )

        return TimelineBuildingOutput(
            document_id=context.document_id,
            status=WORKFLOW_STATUS_COMPLETED,
            events=draft.events,
            evidence=context.evidence,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_evidence(
        self, *, document_id: int, chunks: list[RetrievedChunk]
    ) -> WorkflowEvidence:
        citations: list[WorkflowCitation] = []
        for rank, chunk in enumerate(chunks[: self.max_workflow_citations], start=1):
            citations.append(
                WorkflowCitation(
                    citation_id=f"C{rank}",
                    rank=rank,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text_excerpt=self._excerpt(chunk.text),
                    retrieval_score=chunk.similarity,
                )
            )
        return WorkflowEvidence(citations=citations)

    def _build_system_prompt(self, task_name: str) -> str:
        return (
            "You are a research analyst assistant. "
            f"Return strict JSON for {task_name}. "
            "Use only provided citations, do not fabricate facts, and keep output concise."
        )

    def _build_user_prompt(self, *, context: WorkflowExecutionContext) -> str:
        return (
            f"Document ID: {context.document_id}\n"
            f"Instruction: {context.instruction}\n"
            f"Max items: {self.max_workflow_items}\n"
            f"Max citations: {self.max_workflow_citations}\n"
            "Use citation identifiers exactly as provided below.\n\n"
            f"{context.prompt_context}"
        )

    def _format_prompt_context(self, *, evidence: WorkflowEvidence) -> str:
        if not evidence.citations:
            return f"Evidence:\n- {INSUFFICIENT_EVIDENCE_INSTRUCTION}"

        lines = ["Evidence:"]
        for citation in evidence.citations:
            lines.append(
                (
                    f"- {citation.citation_id} | rank={citation.rank} | "
                    f"chunk_index={citation.chunk_index} | page={citation.page_number} | "
                    f"score={citation.retrieval_score:.3f} | excerpt={citation.text_excerpt}"
                )
            )
        return "\n".join(lines)

    def _validate_citation_ids(
        self, *, citation_ids: Iterable[str], evidence: WorkflowEvidence
    ) -> None:
        allowed_citation_ids = {citation.citation_id for citation in evidence.citations}
        for citation_id in citation_ids:
            if citation_id not in allowed_citation_ids:
                raise ValueError(
                    f"Workflow output referenced unknown citation_id '{citation_id}'."
                )

    @staticmethod
    def _memo_citation_ids(draft: MemoDraft) -> list[str]:
        citations_by_section = draft.citations_by_section
        return [
            *citations_by_section.company_overview,
            *citations_by_section.key_developments,
            *citations_by_section.risks,
            *citations_by_section.catalysts,
            *citations_by_section.kpis,
            *citations_by_section.open_questions,
        ]

    @staticmethod
    def _excerpt(text: str, limit: int = 240) -> str:
        normalized_text = " ".join(text.split())
        if len(normalized_text) <= limit:
            return normalized_text
        return normalized_text[: limit - 3].rstrip() + "..."
