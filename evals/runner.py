from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from evals.schemas import EvalCase, EvalDataset, EvalResult, EvalRunReport, EvalRunSummary

# Keep eval execution local and isolated from production-like environments by default.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:////tmp/research-copilot-stage7-evals.db")
os.environ.setdefault("STORAGE_DIR", "/tmp/research-copilot-stage7-eval-storage")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
backend_dir_str = str(BACKEND_DIR)
if backend_dir_str not in sys.path:
    sys.path.insert(0, backend_dir_str)

DEFAULT_DATASET_PATH = BASE_DIR / "datasets" / "stage7_seed_cases.json"
DEFAULT_RESULTS_DIR = BASE_DIR / "results"

WORKFLOW_ENDPOINT_PATHS: dict[str, str] = {
    "ask": "/documents/{document_id}/ask",
    "memo": "/documents/{document_id}/memo",
    "extract_kpis": "/documents/{document_id}/extract/kpis",
    "extract_risks": "/documents/{document_id}/extract/risks",
    "timeline": "/documents/{document_id}/timeline",
}

ABSTAINING_STATUSES: dict[str, set[str]] = {
    "ask": {"insufficient_evidence"},
    "memo": {"insufficient_evidence"},
    "extract_kpis": {"insufficient_evidence"},
    "extract_risks": {"insufficient_evidence"},
    "timeline": {"insufficient_evidence"},
}

CITATION_ID_PATTERN = re.compile(r"^C[1-9][0-9]*$")


@dataclass(frozen=True)
class SeededDocumentContext:
    document_id: int
    chunk_text_by_index: dict[int, str]


@dataclass(frozen=True)
class ExecutedCase:
    endpoint_path: str
    http_status_code: int
    payload: dict[str, Any]


class _FakeEmbeddingProvider:
    def __init__(self, embedding: list[float]) -> None:
        self._embedding = embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embedding[:] for _ in texts]


class _EvalLLMProvider:
    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[Any],
    ) -> Any:
        del system_prompt, user_prompt

        from app.workflows.schemas import (
            KPIDraft,
            KPIItem,
            MemoCitationsBySection,
            MemoDraft,
            RiskDraft,
            RiskItem,
            TimelineDraft,
            TimelineEvent,
        )

        if response_model is MemoDraft:
            return MemoDraft(
                company_overview=(
                    "Acme reported Q4 revenue growth and highlighted FX volatility as a material risk."
                ),
                key_developments=["Revenue increased 12% in Q4."],
                risks=["FX volatility may pressure margins."],
                catalysts=["Product X launch may support next-quarter demand."],
                kpis=["Revenue reached 120M USD in Q4."],
                open_questions=["Can growth remain above 10% next quarter?"],
                citations_by_section=MemoCitationsBySection(
                    company_overview=["C1"],
                    key_developments=["C1"],
                    risks=["C1"],
                    catalysts=["C1"],
                    kpis=["C1"],
                    open_questions=["C1"],
                ),
            )

        if response_model is KPIDraft:
            return KPIDraft(
                kpis=[
                    KPIItem(
                        name="Revenue",
                        value="120M",
                        unit="USD",
                        period="Q4",
                        citation="C1",
                    )
                ]
            )

        if response_model is RiskDraft:
            return RiskDraft(
                risks=[
                    RiskItem(
                        title="FX volatility",
                        description="Currency fluctuations can affect reported margins.",
                        severity_or_materiality="medium",
                        citation="C1",
                    )
                ]
            )

        if response_model is TimelineDraft:
            return TimelineDraft(
                events=[
                    TimelineEvent(
                        event_date_or_period="2024-10-15",
                        event_summary="Product X was launched.",
                        citation="C1",
                    )
                ]
            )

        raise ValueError(f"Unsupported response_model for eval runner: {response_model}")


class _BackendPatchContext:
    def __init__(self) -> None:
        self._original_embedding_provider = None
        self._original_workflow_service_factory = None

    def __enter__(self) -> "_BackendPatchContext":
        from app.core.config import EMBEDDING_DIMENSION
        from app.retrieval import service as retrieval_service
        from app.api.routes import documents as documents_routes
        from app.workflows.service import StructuredWorkflowService

        self._original_embedding_provider = retrieval_service.get_embedding_provider
        self._original_workflow_service_factory = documents_routes.get_structured_workflow_service

        embedding = [0.0] * EMBEDDING_DIMENSION
        embedding[0] = 1.0
        fake_embedding_provider = _FakeEmbeddingProvider(embedding)

        retrieval_service.get_embedding_provider = lambda: fake_embedding_provider
        documents_routes.get_structured_workflow_service = (
            lambda: StructuredWorkflowService(llm_provider=_EvalLLMProvider())
        )
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        from app.retrieval import service as retrieval_service
        from app.api.routes import documents as documents_routes

        if self._original_embedding_provider is not None:
            retrieval_service.get_embedding_provider = self._original_embedding_provider
        if self._original_workflow_service_factory is not None:
            documents_routes.get_structured_workflow_service = (
                self._original_workflow_service_factory
            )


def _normalize_string(value: Any) -> str:
    return str(value).strip()


def _normalize_excerpt(value: str) -> str:
    normalized = " ".join(value.split())
    if normalized.endswith("..."):
        normalized = normalized[:-3].rstrip()
    return normalized


def load_dataset(dataset_path: Path) -> EvalDataset:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return EvalDataset.model_validate(payload)


def _response_schema_for_workflow(workflow_type: str) -> type[Any]:
    from app.api.routes import documents as documents_routes
    from app.workflows.schemas import (
        KPIExtractionOutput,
        RiskExtractionOutput,
        TimelineBuildingOutput,
    )

    if workflow_type == "ask":
        return documents_routes.DocumentAskResponse
    if workflow_type == "memo":
        return documents_routes.DocumentMemoResponse
    if workflow_type == "extract_kpis":
        return KPIExtractionOutput
    if workflow_type == "extract_risks":
        return RiskExtractionOutput
    if workflow_type == "timeline":
        return TimelineBuildingOutput

    raise ValueError(f"Unsupported workflow_type '{workflow_type}'.")


def _extract_citations(workflow_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if workflow_type == "ask":
        citations = payload.get("citations", [])
        if isinstance(citations, list):
            return [item for item in citations if isinstance(item, dict)]
        return []

    if workflow_type == "memo":
        memo = payload.get("memo")
        if not isinstance(memo, dict):
            return []

        citations_by_section = memo.get("citations_by_section")
        if not isinstance(citations_by_section, dict):
            return []

        citation_ids: list[str] = []
        for values in citations_by_section.values():
            if not isinstance(values, list):
                continue
            for citation_id in values:
                if isinstance(citation_id, str):
                    citation_ids.append(citation_id)

        deduplicated_ids = list(dict.fromkeys(citation_ids))
        return [{"citation_id": citation_id} for citation_id in deduplicated_ids]

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return []

    citations = evidence.get("citations", [])
    if isinstance(citations, list):
        return [item for item in citations if isinstance(item, dict)]
    return []


def _determine_expected_abstention(case: EvalCase) -> bool | None:
    if case.expected_abstention is not None:
        return case.expected_abstention
    if case.expected_status is None:
        return None
    return case.expected_status in ABSTAINING_STATUSES[case.workflow_type]


def _compute_citation_accuracy(
    *,
    citations: list[dict[str, Any]],
    expected_document_id: int,
    chunk_text_by_index: dict[int, str],
) -> tuple[float, list[str]]:
    if not citations:
        return 0.0, ["No citations available for citation accuracy checks."]

    notes: list[str] = []
    checks: list[tuple[str, bool]] = []

    citation_ids = [str(citation.get("citation_id", "")) for citation in citations]
    id_format_ok = all(CITATION_ID_PATTERN.match(citation_id) for citation_id in citation_ids)
    checks.append(("citation_id_format", id_format_ok))
    if not id_format_ok:
        notes.append("Citation IDs must follow C1..Cn format.")

    has_rank_details = all("rank" in citation for citation in citations)
    if has_rank_details:
        unique_ids_ok = len(set(citation_ids)) == len(citation_ids)
        checks.append(("citation_id_uniqueness", unique_ids_ok))
        if not unique_ids_ok:
            notes.append("Citation IDs must be unique per response.")

        rank_values = [citation.get("rank") for citation in citations]
        rank_sequence_ok = [int(rank) for rank in rank_values] == list(
            range(1, len(citations) + 1)
        )
        checks.append(("citation_rank_sequence", rank_sequence_ok))
        if not rank_sequence_ok:
            notes.append("Citation ranks must be sequential starting at 1.")

    has_document_details = all("document_id" in citation for citation in citations)
    if has_document_details:
        document_match_ok = all(
            int(citation.get("document_id", -1)) == expected_document_id
            for citation in citations
        )
        checks.append(("citation_document_match", document_match_ok))
        if not document_match_ok:
            notes.append("Citation document_id does not match the evaluated document.")

    has_chunk_details = all("chunk_index" in citation for citation in citations)
    if has_chunk_details:
        chunk_index_match_ok = all(
            int(citation.get("chunk_index", -1)) in chunk_text_by_index
            for citation in citations
        )
        checks.append(("citation_chunk_match", chunk_index_match_ok))
        if not chunk_index_match_ok:
            notes.append("Citation chunk_index does not exist in the seeded document.")

    has_excerpt_details = all(
        "text_excerpt" in citation and "chunk_index" in citation
        for citation in citations
    )
    if has_excerpt_details:
        excerpt_match_ok = True
        for citation in citations:
            chunk_index = int(citation.get("chunk_index", -1))
            expected_chunk_text = chunk_text_by_index.get(chunk_index)
            if expected_chunk_text is None:
                excerpt_match_ok = False
                break

            excerpt = _normalize_excerpt(str(citation.get("text_excerpt", "")))
            if not excerpt:
                excerpt_match_ok = False
                break

            if excerpt.lower() not in " ".join(expected_chunk_text.split()).lower():
                excerpt_match_ok = False
                break

        checks.append(("citation_excerpt_grounded", excerpt_match_ok))
        if not excerpt_match_ok:
            notes.append("Citation excerpt is not grounded in the referenced chunk text.")

    passed_checks = sum(1 for _, is_ok in checks if is_ok)
    score = passed_checks / len(checks)
    return round(score, 6), notes


async def _post_case_request(path: str, payload: dict[str, Any]) -> httpx.Response:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(path, json=payload)


def _execute_case(case: EvalCase, document_id: int) -> ExecutedCase:
    endpoint_template = WORKFLOW_ENDPOINT_PATHS[case.workflow_type]
    endpoint_path = endpoint_template.format(document_id=document_id)
    response = asyncio.run(_post_case_request(endpoint_path, case.input))

    payload: dict[str, Any]
    try:
        parsed = response.json()
        payload = parsed if isinstance(parsed, dict) else {"_payload": parsed}
    except ValueError:
        payload = {"_raw_response": response.text}

    return ExecutedCase(
        endpoint_path=endpoint_path,
        http_status_code=response.status_code,
        payload=payload,
    )


def evaluate_case(
    *,
    case: EvalCase,
    execution: ExecutedCase,
    expected_document_id: int,
    chunk_text_by_index: dict[int, str],
) -> EvalResult:
    notes: list[str] = []
    observed_status_raw = execution.payload.get("status")
    observed_status = str(observed_status_raw) if observed_status_raw is not None else None

    schema_adherence = 0.0
    if execution.http_status_code == 200:
        response_model = _response_schema_for_workflow(case.workflow_type)
        try:
            response_model.model_validate(execution.payload)
            schema_adherence = 1.0
        except ValidationError as exc:
            notes.append(f"Schema validation failed: {exc.errors()}")
    else:
        notes.append(
            f"Workflow request failed with HTTP {execution.http_status_code}: "
            + _normalize_string(execution.payload)
        )

    expected_status_match = 1.0
    if case.expected_status is not None:
        expected_status_match = 1.0 if observed_status == case.expected_status else 0.0
        if expected_status_match == 0.0:
            notes.append(
                f"Expected status '{case.expected_status}', observed '{observed_status}'."
            )

    expected_abstention = _determine_expected_abstention(case)
    observed_abstention = (
        observed_status in ABSTAINING_STATUSES[case.workflow_type]
        if observed_status is not None
        else False
    )

    abstention_correctness = 1.0
    if expected_abstention is not None:
        abstention_correctness = 1.0 if observed_abstention == expected_abstention else 0.0
        if abstention_correctness == 0.0:
            notes.append(
                "Abstention behavior mismatch: "
                f"expected_abstention={expected_abstention}, observed_abstention={observed_abstention}."
            )

    expected_fields_adherence = 1.0
    if case.expected_fields is not None:
        missing_fields = [
            field_name
            for field_name in case.expected_fields
            if field_name not in execution.payload
        ]
        expected_fields_adherence = 1.0 if not missing_fields else 0.0
        if missing_fields:
            notes.append(
                "Missing expected fields in response: " + ", ".join(sorted(missing_fields))
            )

    citations = _extract_citations(case.workflow_type, execution.payload)
    citation_presence = 1.0 if observed_abstention or len(citations) > 0 else 0.0
    if citation_presence == 0.0:
        notes.append("Non-abstained output did not include citations.")

    if observed_abstention:
        citation_accuracy = 1.0
    else:
        citation_accuracy, citation_accuracy_notes = _compute_citation_accuracy(
            citations=citations,
            expected_document_id=expected_document_id,
            chunk_text_by_index=chunk_text_by_index,
        )
        notes.extend(citation_accuracy_notes)

    metrics = {
        "schema_adherence": schema_adherence,
        "abstention_correctness": abstention_correctness,
        "citation_presence": citation_presence,
        "citation_accuracy": citation_accuracy,
        "expected_status_match": expected_status_match,
        "expected_fields_adherence": expected_fields_adherence,
    }

    required_metrics = (
        "schema_adherence",
        "abstention_correctness",
        "citation_presence",
        "citation_accuracy",
    )
    required_metrics_pass = all(metrics[name] == 1.0 for name in required_metrics)
    pass_fail = (
        "pass"
        if required_metrics_pass
        and metrics["expected_status_match"] == 1.0
        and metrics["expected_fields_adherence"] == 1.0
        else "fail"
    )

    return EvalResult(
        case_id=case.id,
        workflow_type=case.workflow_type,
        pass_fail=pass_fail,
        endpoint_path=execution.endpoint_path,
        http_status_code=execution.http_status_code,
        observed_status=observed_status,
        metrics=metrics,
        notes=notes,
    )


def _reset_database() -> None:
    from app.db.database import Base, create_tables, engine

    Base.metadata.drop_all(bind=engine)
    create_tables()


def _seed_documents(dataset: EvalDataset) -> dict[str, SeededDocumentContext]:
    from app.core.config import EMBEDDING_DIMENSION
    from app.db.database import SessionLocal
    from app.db.models.document import Document
    from app.db.models.document_chunk import DocumentChunk

    embedding = [0.0] * EMBEDDING_DIMENSION
    embedding[0] = 1.0

    contexts: dict[str, SeededDocumentContext] = {}

    db = SessionLocal()
    try:
        for fixture in dataset.document_fixtures:
            document = Document(
                company_name=fixture.company_name,
                document_type=fixture.document_type,
                period=fixture.period,
                source_filename=fixture.source_filename,
                storage_path=f"evals/{fixture.reference_id}/{fixture.source_filename}",
                status=fixture.status,
            )
            db.add(document)
            db.flush()

            chunk_text_by_index: dict[int, str] = {}
            for chunk in sorted(fixture.chunks, key=lambda item: item.chunk_index):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        embedding=embedding,
                    )
                )
                chunk_text_by_index[chunk.chunk_index] = chunk.text

            db.commit()
            db.refresh(document)
            contexts[fixture.reference_id] = SeededDocumentContext(
                document_id=document.id,
                chunk_text_by_index=chunk_text_by_index,
            )
    finally:
        db.close()

    return contexts


def run_eval_dataset(dataset: EvalDataset) -> EvalRunReport:
    _reset_database()
    document_contexts = _seed_documents(dataset)

    results: list[EvalResult] = []
    with _BackendPatchContext():
        for case in dataset.cases:
            context = document_contexts[case.document_reference.reference_id]
            execution = _execute_case(case, context.document_id)
            result = evaluate_case(
                case=case,
                execution=execution,
                expected_document_id=context.document_id,
                chunk_text_by_index=context.chunk_text_by_index,
            )
            results.append(result)

    passed_cases = sum(1 for result in results if result.pass_fail == "pass")
    failed_cases = len(results) - passed_cases

    now = datetime.now(timezone.utc)
    run_id = now.strftime("stage7-local-%Y%m%dT%H%M%SZ")

    return EvalRunReport(
        run_id=run_id,
        generated_at=now,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.version,
        results=results,
        summary=EvalRunSummary(
            total_cases=len(results),
            passed_cases=passed_cases,
            failed_cases=failed_cases,
        ),
    )


def write_json_report(report: EvalRunReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown_report(report: EvalRunReport, output_path: Path) -> None:
    lines = [
        f"# Eval Report {report.run_id}",
        "",
        f"- Dataset: `{report.dataset_id}`",
        f"- Version: `{report.dataset_version}`",
        f"- Generated At: `{report.generated_at.isoformat()}`",
        f"- Total Cases: `{report.summary.total_cases}`",
        f"- Passed: `{report.summary.passed_cases}`",
        f"- Failed: `{report.summary.failed_cases}`",
        "",
        "| case_id | workflow | status | http | schema | abstention | citation_presence | citation_accuracy |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]

    for result in report.results:
        schema = result.metrics.get("schema_adherence", 0.0)
        abstention = result.metrics.get("abstention_correctness", 0.0)
        citation_presence = result.metrics.get("citation_presence", 0.0)
        citation_accuracy = result.metrics.get("citation_accuracy", 0.0)
        lines.append(
            "| "
            + f"{result.case_id} | {result.workflow_type} | {result.pass_fail} | "
            + f"{result.http_status_code} | {schema:.2f} | {abstention:.2f} | "
            + f"{citation_presence:.2f} | {citation_accuracy:.2f} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for result in report.results:
        if not result.notes:
            continue
        lines.append(f"- `{result.case_id}`")
        for note in result.notes:
            lines.append(f"  - {note}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_json_output_path(output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"stage7_eval_report_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Stage 7 local evals against existing research workflow endpoints."
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to eval dataset JSON file.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional output JSON report path. Defaults to evals/results/<timestamp>.json",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Optional output Markdown report path. Defaults to same basename as JSON.",
    )
    parser.add_argument(
        "--skip-markdown",
        action="store_true",
        help="Do not write markdown report output.",
    )
    parser.add_argument(
        "--fail-on-fail",
        action="store_true",
        help="Return exit code 1 if any case fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset)

    try:
        dataset = load_dataset(dataset_path)
    except FileNotFoundError:
        print(f"Dataset not found: {dataset_path}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"Dataset JSON parsing failed: {exc}")
        return 2
    except ValidationError as exc:
        print("Dataset validation failed:")
        print(exc)
        return 2

    report = run_eval_dataset(dataset)

    json_output_path = build_json_output_path(args.output_json)
    write_json_report(report, json_output_path)

    markdown_output_path: Path | None = None
    if not args.skip_markdown:
        markdown_output_path = (
            Path(args.output_md)
            if args.output_md is not None
            else json_output_path.with_suffix(".md")
        )
        write_markdown_report(report, markdown_output_path)

    print(f"Loaded dataset: {dataset_path}")
    print(f"Cases: {report.summary.total_cases}")
    print(f"Passed: {report.summary.passed_cases}")
    print(f"Failed: {report.summary.failed_cases}")
    print(f"JSON report: {json_output_path}")
    if markdown_output_path is not None:
        print(f"Markdown report: {markdown_output_path}")

    if report.summary.failed_cases > 0:
        print("Failed cases:")
        for result in report.results:
            if result.pass_fail == "pass":
                continue
            details = " | ".join(result.notes) if result.notes else "No details."
            print(f"- {result.case_id}: {details}")

    if args.fail_on_fail and report.summary.failed_cases > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
