import asyncio
from typing import Any

import pytest

from mcp_server.config import MCPServerSettings
from mcp_server.server import create_mcp_server
from mcp_server.tools import workflows as workflow_tools


def _settings() -> MCPServerSettings:
    return MCPServerSettings(
        server_name="Research Copilot MCP Test",
        transport="stdio",
        backend_base_url="http://127.0.0.1:8000",
        database_url="sqlite+pysqlite:////tmp/research-copilot-mcp-test.db",
        host="127.0.0.1",
        port=8811,
        mount_path="/",
    )


def _extract_structured_tool_output(result: object) -> dict[str, Any]:
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
        return result[1]
    if isinstance(result, dict):
        return result
    raise AssertionError(f"Unexpected MCP call_tool result shape: {result!r}")


def test_ask_document_from_backend_preserves_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "question": "What was free cash flow?",
        "answer": "Insufficient evidence to answer the question from retrieved context.",
        "status": "insufficient_evidence",
        "citations": [],
    }

    monkeypatch.setattr(workflow_tools, "_request_backend_json", lambda **kwargs: payload)

    output = workflow_tools.ask_document_from_backend(
        settings=_settings(),
        document_id=1,
        question="What was free cash flow?",
    )

    assert output.tool == "ask_document"
    assert output.status == "insufficient_evidence"
    assert output.citations == []


def test_generate_memo_from_backend_generated_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "document_id": 1,
        "status": "generated",
        "memo": {
            "company_overview": "Acme reported strong quarter growth.",
            "key_developments": ["Revenue increased 12 percent in Q4."],
            "risks": ["FX volatility remains elevated."],
            "catalysts": ["Product X launch can support next-quarter demand."],
            "kpis": ["Revenue reached 120M USD."],
            "open_questions": ["Can growth remain above 10 percent?"],
            "citations_by_section": {
                "company_overview": ["C1"],
                "key_developments": ["C1"],
                "risks": ["C1"],
                "catalysts": ["C1"],
                "kpis": ["C1"],
                "open_questions": ["C1"],
            },
        },
    }

    monkeypatch.setattr(workflow_tools, "_request_backend_json", lambda **kwargs: payload)

    output = workflow_tools.generate_memo_from_backend(settings=_settings(), document_id=1)

    assert output.tool == "generate_memo"
    assert output.status == "generated"
    assert output.memo is not None
    assert output.memo.company_overview.startswith("Acme")


def test_extract_risks_from_backend_preserves_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "workflow": "risk_extraction",
        "document_id": 1,
        "status": "insufficient_evidence",
        "risks": [],
        "evidence": {"citations": []},
    }

    monkeypatch.setattr(workflow_tools, "_request_backend_json", lambda **kwargs: payload)

    output = workflow_tools.extract_risks_from_backend(settings=_settings(), document_id=1)

    assert output.tool == "extract_risks"
    assert output.workflow == "risk_extraction"
    assert output.status == "insufficient_evidence"
    assert output.risks == []
    assert output.evidence.citations == []


def test_ask_document_from_backend_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="question"):
        workflow_tools.ask_document_from_backend(
            settings=_settings(),
            document_id=1,
            question="   ",
        )


def test_registered_workflow_tools_can_be_invoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request_backend_json(
        *,
        base_url: str,
        path: str,
        method: str = "GET",
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        assert base_url == "http://127.0.0.1:8000"

        if path == "/documents/7/ask":
            assert method == "POST"
            assert body is not None
            assert body["question"] == "What changed in revenue in Q4?"
            return {
                "question": body["question"],
                "answer": "Revenue increased 12 percent in Q4.",
                "status": "answered",
                "citations": [
                    {
                        "citation_id": "C1",
                        "rank": 1,
                        "document_id": 7,
                        "chunk_index": 0,
                        "page_number": 1,
                        "text_excerpt": "Revenue increased 12 percent in Q4.",
                        "retrieval_score": 0.91,
                    }
                ],
            }

        if path == "/documents/7/memo":
            assert method == "POST"
            return {
                "document_id": 7,
                "status": "generated",
                "memo": {
                    "company_overview": "Acme reported strong quarter growth.",
                    "key_developments": ["Revenue increased 12 percent in Q4."],
                    "risks": ["FX volatility remains elevated."],
                    "catalysts": ["Product X launch can support next-quarter demand."],
                    "kpis": ["Revenue reached 120M USD."],
                    "open_questions": ["Can growth remain above 10 percent?"],
                    "citations_by_section": {
                        "company_overview": ["C1"],
                        "key_developments": ["C1"],
                        "risks": ["C1"],
                        "catalysts": ["C1"],
                        "kpis": ["C1"],
                        "open_questions": ["C1"],
                    },
                },
            }

        if path == "/documents/7/extract/risks":
            assert method == "POST"
            return {
                "workflow": "risk_extraction",
                "document_id": 7,
                "status": "completed",
                "risks": [
                    {
                        "title": "FX volatility",
                        "description": "Currency swings can pressure margins.",
                        "severity_or_materiality": "medium",
                        "citation": "C1",
                    }
                ],
                "evidence": {
                    "citations": [
                        {
                            "citation_id": "C1",
                            "rank": 1,
                            "document_id": 7,
                            "chunk_index": 0,
                            "page_number": 1,
                            "text_excerpt": "Management highlighted foreign exchange volatility.",
                            "retrieval_score": 0.88,
                        }
                    ]
                },
            }

        raise AssertionError(f"Unexpected backend call: {method} {path}")

    monkeypatch.setattr(workflow_tools, "_request_backend_json", fake_request_backend_json)

    server = create_mcp_server(_settings())

    ask_result = asyncio.run(
        server.call_tool(
            "ask_document",
            {
                "document_id": 7,
                "question": "What changed in revenue in Q4?",
            },
        )
    )
    ask_payload = _extract_structured_tool_output(ask_result)
    assert ask_payload["tool"] == "ask_document"
    assert ask_payload["status"] == "answered"
    assert ask_payload["citations"][0]["citation_id"] == "C1"

    memo_result = asyncio.run(server.call_tool("generate_memo", {"document_id": 7}))
    memo_payload = _extract_structured_tool_output(memo_result)
    assert memo_payload["tool"] == "generate_memo"
    assert memo_payload["status"] == "generated"
    assert memo_payload["memo"]["citations_by_section"]["kpis"] == ["C1"]

    risks_result = asyncio.run(server.call_tool("extract_risks", {"document_id": 7}))
    risks_payload = _extract_structured_tool_output(risks_result)
    assert risks_payload["tool"] == "extract_risks"
    assert risks_payload["status"] == "completed"
    assert risks_payload["risks"][0]["title"] == "FX volatility"
