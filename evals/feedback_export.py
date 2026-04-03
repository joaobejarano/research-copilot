from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / "results"
DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:////tmp/research-copilot-feedback.db")

SUPPORTED_EVAL_WORKFLOWS = {
    "ask",
    "memo",
    "extract_kpis",
    "extract_risks",
    "timeline",
}

WORKFLOW_EXPECTED_FIELDS: dict[str, list[str]] = {
    "ask": ["question", "answer", "status", "citations"],
    "memo": ["document_id", "status", "memo"],
    "extract_kpis": ["workflow", "document_id", "status", "kpis", "evidence"],
    "extract_risks": ["workflow", "document_id", "status", "risks", "evidence"],
    "timeline": ["workflow", "document_id", "status", "events", "evidence"],
}


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized if normalized else None


def _extract_ask_target_details(target_reference: str | None) -> tuple[str | None, str | None]:
    if target_reference is None:
        return None, None

    prefix, separator, remainder = target_reference.partition(":")
    if prefix != "ask" or separator == "":
        return None, None

    status, separator, question = remainder.partition(":")
    if separator == "":
        return None, None

    normalized_question = _normalize_text(question)
    normalized_status = _normalize_text(status)
    if normalized_status not in {"answered", "insufficient_evidence"}:
        normalized_status = None

    return normalized_question, normalized_status


def _build_case_input(
    *,
    workflow_type: str,
    feedback_id: int,
    target_reference: str | None,
    reason: str | None,
) -> tuple[dict[str, Any], str | None]:
    if workflow_type == "ask":
        parsed_question, parsed_status = _extract_ask_target_details(target_reference)
        question = parsed_question or f"TODO: investigate ask issue from feedback #{feedback_id}."
        return (
            {
                "question": question,
                "top_k": 5,
                "min_similarity": 0.2,
            },
            parsed_status,
        )

    base_instruction = (
        f"Re-run {workflow_type} and investigate the issue captured in feedback #{feedback_id}."
    )
    normalized_reason = _normalize_text(reason)
    if normalized_reason is not None:
        base_instruction = f"{base_instruction} Focus: {normalized_reason}"

    return (
        {
            "instruction": base_instruction,
            "top_k": 5,
            "min_similarity": 0.2,
        },
        None,
    )


def build_follow_up_candidate(row: dict[str, Any]) -> dict[str, Any]:
    workflow_type = str(row["workflow_type"])
    feedback_id = int(row["feedback_id"])

    reason = _normalize_text(row.get("reason"))
    reviewer_note = _normalize_text(row.get("reviewer_note"))
    target_reference = _normalize_text(row.get("target_reference"))

    case_input, expected_status = _build_case_input(
        workflow_type=workflow_type,
        feedback_id=feedback_id,
        target_reference=target_reference,
        reason=reason,
    )

    behavior_parts = [
        f"Follow up negative feedback #{feedback_id} for workflow '{workflow_type}'.",
    ]
    if reason is not None:
        behavior_parts.append(f"Reason: {reason}")
    if reviewer_note is not None:
        behavior_parts.append(f"Reviewer note: {reviewer_note}")

    expected_abstention: bool | None = None
    if expected_status == "insufficient_evidence":
        expected_abstention = True

    eval_case_candidate = {
        "id": f"feedback_followup_{feedback_id}_{workflow_type}",
        "workflow_type": workflow_type,
        "document_reference": {
            "reference_id": f"document_{int(row['document_id'])}",
            "document_id": int(row["document_id"]),
            "source_filename": row.get("source_filename"),
            "notes": (
                "Derived from stored reviewer feedback. "
                "Map this reference to a fixture before running evals."
            ),
        },
        "input": case_input,
        "expected_behavior": " ".join(behavior_parts),
        "expected_fields": WORKFLOW_EXPECTED_FIELDS[workflow_type],
    }

    if expected_status is not None:
        eval_case_candidate["expected_status"] = expected_status
    if expected_abstention is not None:
        eval_case_candidate["expected_abstention"] = expected_abstention

    return {
        "feedback_id": feedback_id,
        "workflow_type": workflow_type,
        "document_id": int(row["document_id"]),
        "feedback_created_at": row.get("created_at"),
        "feedback_value": row.get("feedback_value"),
        "reason": reason,
        "reviewer_note": reviewer_note,
        "target_reference": target_reference,
        "eval_case_candidate": eval_case_candidate,
    }


def fetch_feedback_rows(
    *,
    database_url: str,
    feedback_value: str | None,
    workflow_type: str | None,
    document_id: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    engine = create_engine(database_url, pool_pre_ping=True)

    query = text(
        """
        SELECT
            f.id AS feedback_id,
            f.workflow_type AS workflow_type,
            f.document_id AS document_id,
            f.target_id AS target_id,
            f.target_reference AS target_reference,
            f.feedback_value AS feedback_value,
            f.reason AS reason,
            f.reviewer_note AS reviewer_note,
            f.created_at AS created_at,
            d.company_name AS company_name,
            d.document_type AS document_type,
            d.period AS period,
            d.source_filename AS source_filename
        FROM feedback AS f
        LEFT JOIN documents AS d ON d.id = f.document_id
        WHERE (:workflow_type IS NULL OR f.workflow_type = :workflow_type)
          AND (:document_id IS NULL OR f.document_id = :document_id)
          AND (:feedback_value IS NULL OR f.feedback_value = :feedback_value)
        ORDER BY f.created_at DESC, f.id DESC
        LIMIT :limit
        """
    )

    try:
        with engine.begin() as connection:
            rows = connection.execute(
                query,
                {
                    "workflow_type": workflow_type,
                    "document_id": document_id,
                    "feedback_value": feedback_value,
                    "limit": limit,
                },
            ).mappings()
            return [dict(row) for row in rows]
    except SQLAlchemyError as exc:  # pragma: no cover - covered via CLI behavior check.
        raise RuntimeError(
            "Could not read feedback rows. Ensure feedback/documents tables exist and DATABASE_URL is correct."
        ) from exc
    finally:
        engine.dispose()


def build_follow_up_export(
    *,
    rows: list[dict[str, Any]],
    source_database_url: str,
    feedback_value_filter: str,
    workflow_type_filter: str | None,
    document_id_filter: int | None,
    limit: int,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in rows:
        workflow_type = str(row.get("workflow_type", ""))
        feedback_id = int(row.get("feedback_id", 0))

        if workflow_type not in SUPPORTED_EVAL_WORKFLOWS:
            skipped.append(
                {
                    "feedback_id": feedback_id,
                    "workflow_type": workflow_type,
                    "why": "workflow_type is not supported by the Stage 7 eval runner.",
                }
            )
            continue

        candidates.append(build_follow_up_candidate(row))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "database_url": source_database_url,
            "filters": {
                "feedback_value": feedback_value_filter,
                "workflow_type": workflow_type_filter,
                "document_id": document_id_filter,
                "limit": limit,
            },
        },
        "summary": {
            "feedback_rows_scanned": len(rows),
            "candidate_cases_generated": len(candidates),
            "skipped_rows": len(skipped),
        },
        "candidates": candidates,
        "skipped": skipped,
    }


def build_output_path(output_arg: str | None) -> Path:
    if output_arg is not None:
        return Path(output_arg)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"feedback_followup_candidates_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export stored reviewer feedback into follow-up eval candidate cases "
            "for future Stage 7 dataset iteration."
        )
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DB_URL,
        help="Database URL that contains feedback/documents tables.",
    )
    parser.add_argument(
        "--feedback-value",
        choices=["negative", "positive", "all"],
        default="negative",
        help="Feedback value filter. Default: negative (recommended for follow-up opportunities).",
    )
    parser.add_argument(
        "--workflow-type",
        default=None,
        help="Optional workflow_type filter.",
    )
    parser.add_argument(
        "--document-id",
        type=int,
        default=None,
        help="Optional document_id filter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum feedback rows to scan.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to evals/results/feedback_followup_candidates_<timestamp>.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    feedback_value_filter = None if args.feedback_value == "all" else args.feedback_value

    try:
        rows = fetch_feedback_rows(
            database_url=args.database_url,
            feedback_value=feedback_value_filter,
            workflow_type=args.workflow_type,
            document_id=args.document_id,
            limit=args.limit,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    export_payload = build_follow_up_export(
        rows=rows,
        source_database_url=args.database_url,
        feedback_value_filter=args.feedback_value,
        workflow_type_filter=args.workflow_type,
        document_id_filter=args.document_id,
        limit=args.limit,
    )

    output_path = build_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Scanned feedback rows: {export_payload['summary']['feedback_rows_scanned']}")
    print(f"Generated candidate cases: {export_payload['summary']['candidate_cases_generated']}")
    print(f"Skipped rows: {export_payload['summary']['skipped_rows']}")
    print(f"Output: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
