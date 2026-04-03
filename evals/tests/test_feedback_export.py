from pathlib import Path

from sqlalchemy import create_engine, text

from evals.feedback_export import (
    _extract_ask_target_details,
    build_follow_up_candidate,
    build_follow_up_export,
    fetch_feedback_rows,
)


def _seed_sqlite_feedback_db(db_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    period TEXT NOT NULL,
                    source_filename TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE feedback (
                    id INTEGER PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    document_id INTEGER NOT NULL,
                    target_id INTEGER NULL,
                    target_reference TEXT NULL,
                    feedback_value TEXT NOT NULL,
                    reason TEXT NULL,
                    reviewer_note TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        )

        connection.execute(
            text(
                """
                INSERT INTO documents (id, company_name, document_type, period, source_filename)
                VALUES (1, 'Acme Corp', 'financial_report', '2024-Q4', 'acme_q4_report.txt')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO feedback (
                    id,
                    workflow_type,
                    document_id,
                    target_id,
                    target_reference,
                    feedback_value,
                    reason,
                    reviewer_note,
                    created_at
                ) VALUES
                    (
                        10,
                        'ask',
                        1,
                        NULL,
                        'ask:answered:What happened to revenue in Q4?',
                        'negative',
                        'Answer ignored FX impact context.',
                        'Needs stronger risk grounding.',
                        '2026-04-03T15:00:00Z'
                    ),
                    (
                        11,
                        'agent',
                        1,
                        NULL,
                        'agent:trace:abc',
                        'negative',
                        'Agent selected an unnecessary tool.',
                        NULL,
                        '2026-04-03T16:00:00Z'
                    ),
                    (
                        12,
                        'memo',
                        1,
                        NULL,
                        'memo:latest',
                        'positive',
                        NULL,
                        'Memo was concise and grounded.',
                        '2026-04-03T17:00:00Z'
                    )
                """
            )
        )

    engine.dispose()
    return database_url


def test_extract_ask_target_details_parses_expected_shape() -> None:
    question, status = _extract_ask_target_details("ask:insufficient_evidence:What is free cash flow?")

    assert question == "What is free cash flow?"
    assert status == "insufficient_evidence"


def test_build_follow_up_candidate_maps_to_eval_case_template() -> None:
    candidate = build_follow_up_candidate(
        {
            "feedback_id": 42,
            "workflow_type": "ask",
            "document_id": 7,
            "target_reference": "ask:answered:When was Product X launched?",
            "feedback_value": "negative",
            "reason": "Missing launch date citation.",
            "reviewer_note": "Should cite primary source chunk.",
            "created_at": "2026-04-03T10:00:00Z",
            "source_filename": "acme_q4_report.txt",
        }
    )

    assert candidate["feedback_id"] == 42
    assert candidate["workflow_type"] == "ask"
    assert candidate["reason"] == "Missing launch date citation."

    eval_case = candidate["eval_case_candidate"]
    assert eval_case["id"] == "feedback_followup_42_ask"
    assert eval_case["workflow_type"] == "ask"
    assert eval_case["document_reference"]["document_id"] == 7
    assert eval_case["input"]["question"] == "When was Product X launched?"
    assert eval_case["expected_status"] == "answered"
    assert "expected_abstention" not in eval_case


def test_fetch_feedback_rows_and_build_export_identifies_negative_follow_ups(
    tmp_path: Path,
) -> None:
    database_url = _seed_sqlite_feedback_db(tmp_path / "feedback_export.db")

    rows = fetch_feedback_rows(
        database_url=database_url,
        feedback_value="negative",
        workflow_type=None,
        document_id=None,
        limit=20,
    )

    assert len(rows) == 2
    assert rows[0]["feedback_id"] == 11
    assert rows[1]["feedback_id"] == 10

    export_payload = build_follow_up_export(
        rows=rows,
        source_database_url=database_url,
        feedback_value_filter="negative",
        workflow_type_filter=None,
        document_id_filter=None,
        limit=20,
    )

    assert export_payload["summary"]["feedback_rows_scanned"] == 2
    assert export_payload["summary"]["candidate_cases_generated"] == 1
    assert export_payload["summary"]["skipped_rows"] == 1

    skipped = export_payload["skipped"]
    assert skipped[0]["workflow_type"] == "agent"

    candidates = export_payload["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["workflow_type"] == "ask"
    assert candidates[0]["eval_case_candidate"]["expected_fields"] == [
        "question",
        "answer",
        "status",
        "citations",
    ]
