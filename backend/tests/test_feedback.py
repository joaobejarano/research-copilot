import asyncio

import httpx

from app.db.database import SessionLocal
from app.db.models.document import Document
from app.main import app


def _seed_document(*, period: str = "2024-Q4") -> int:
    db = SessionLocal()
    try:
        document = Document(
            company_name="Acme Corp",
            document_type="financial_report",
            period=period,
            source_filename="report.txt",
            storage_path=f"Acme_Corp/financial_report/{period}/1.txt",
            status="ready",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document.id
    finally:
        db.close()


def _post_feedback(payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post("/feedback", json=payload)

    return asyncio.run(request())


def _get_feedback(path: str = "/feedback") -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path)

    return asyncio.run(request())


def test_create_feedback_persists_review_result() -> None:
    document_id = _seed_document()

    response = _post_feedback(
        {
            "workflow_type": "ask",
            "document_id": document_id,
            "target_reference": "answer:ask_revenue_q4",
            "feedback_value": "positive",
            "reviewer_note": "Grounded and useful answer.",
        }
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] >= 1
    assert payload["workflow_type"] == "ask"
    assert payload["document_id"] == document_id
    assert payload["target_id"] is None
    assert payload["target_reference"] == "answer:ask_revenue_q4"
    assert payload["feedback_value"] == "positive"
    assert payload["reason"] is None
    assert payload["reviewer_note"] == "Grounded and useful answer."
    assert payload["created_at"]


def test_create_feedback_requires_reason_for_negative_value() -> None:
    document_id = _seed_document()

    response = _post_feedback(
        {
            "workflow_type": "memo",
            "document_id": document_id,
            "feedback_value": "negative",
            "reviewer_note": "The memo omitted a key risk.",
        }
    )

    assert response.status_code == 422
    assert "reason is required when feedback_value is negative" in str(response.json())


def test_create_negative_feedback_with_reason_persists() -> None:
    document_id = _seed_document()

    response = _post_feedback(
        {
            "workflow_type": "ask",
            "document_id": document_id,
            "target_reference": "ask:answered:What happened to revenue in Q4?",
            "feedback_value": "negative",
            "reason": "Answer did not address cited risk details.",
            "reviewer_note": "Need clearer risk grounding.",
        }
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["workflow_type"] == "ask"
    assert payload["feedback_value"] == "negative"
    assert payload["reason"] == "Answer did not address cited risk details."
    assert payload["reviewer_note"] == "Need clearer risk grounding."


def test_create_feedback_returns_404_for_missing_document() -> None:
    response = _post_feedback(
        {
            "workflow_type": "extract_kpis",
            "document_id": 999,
            "feedback_value": "positive",
        }
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}


def test_list_feedback_returns_feedback_and_supports_filters() -> None:
    doc_a = _seed_document(period="2024-Q4")
    doc_b = _seed_document(period="2025-Q1")

    create_a = _post_feedback(
        {
            "workflow_type": "ask",
            "document_id": doc_a,
            "feedback_value": "positive",
            "target_reference": "answer:ask_management_risk",
        }
    )
    create_b = _post_feedback(
        {
            "workflow_type": "memo",
            "document_id": doc_a,
            "target_id": 12,
            "feedback_value": "negative",
            "reason": "Missing FX risk context.",
        }
    )
    create_c = _post_feedback(
        {
            "workflow_type": "timeline",
            "document_id": doc_b,
            "feedback_value": "positive",
            "reviewer_note": "Timeline sequencing is clear.",
        }
    )

    assert create_a.status_code == 201
    assert create_b.status_code == 201
    assert create_c.status_code == 201

    all_feedback = _get_feedback()
    assert all_feedback.status_code == 200
    all_payload = all_feedback.json()
    assert len(all_payload) == 3
    assert all_payload[0]["id"] > all_payload[1]["id"] > all_payload[2]["id"]

    filtered_by_document = _get_feedback(f"/feedback?document_id={doc_a}")
    assert filtered_by_document.status_code == 200
    filtered_document_payload = filtered_by_document.json()
    assert len(filtered_document_payload) == 2
    assert all(item["document_id"] == doc_a for item in filtered_document_payload)

    filtered_by_workflow = _get_feedback("/feedback?workflow_type=ask")
    assert filtered_by_workflow.status_code == 200
    filtered_workflow_payload = filtered_by_workflow.json()
    assert len(filtered_workflow_payload) == 1
    assert filtered_workflow_payload[0]["workflow_type"] == "ask"

    filtered_by_negative = _get_feedback("/feedback?feedback_value=negative")
    assert filtered_by_negative.status_code == 200
    filtered_negative_payload = filtered_by_negative.json()
    assert len(filtered_negative_payload) == 1
    assert filtered_negative_payload[0]["feedback_value"] == "negative"
    assert filtered_negative_payload[0]["reason"] == "Missing FX risk context."

    limited_feedback = _get_feedback("/feedback?limit=2")
    assert limited_feedback.status_code == 200
    limited_payload = limited_feedback.json()
    assert len(limited_payload) == 2
    assert limited_payload[0]["id"] > limited_payload[1]["id"]
