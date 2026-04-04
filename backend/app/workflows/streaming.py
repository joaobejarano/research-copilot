"""Server-Sent Events (SSE) streaming generators for long-running workflows.

Each generator yields SSE-formatted strings in three phases:
  1. ``status`` / ``retrieving`` — emitted before the DB retrieval step.
  2. ``status`` / ``generating`` — emitted after retrieval, before the LLM call.
  3. ``result``                  — emitted with the full JSON payload on success.
  4. ``error``                   — emitted instead of ``result`` on failure.

SSE wire format (each event ends with a blank line):
    data: {"type": "status", "step": "retrieving", "message": "..."}\\n\\n
    data: {"type": "result",  "payload": {...}}\\n\\n

The generators run synchronous service calls inline (consistent with how the
rest of the FastAPI routes work).  Each ``yield`` delivers the buffered event
to the client before the next blocking call starts.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.workflows.schemas import (
    KPIExtractionRequest,
    MemoGenerationRequest,
    RiskExtractionRequest,
    TimelineBuildingRequest,
)
from app.workflows.service import StructuredWorkflowService


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def stream_memo_workflow(
    *,
    db: Session,
    request: MemoGenerationRequest,
) -> AsyncIterator[str]:
    service = StructuredWorkflowService()

    yield _sse({"type": "status", "step": "retrieving", "message": "Retrieving relevant context..."})

    try:
        context = service.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "status", "step": "generating", "message": "Generating memo..."})

    try:
        result = service._execute_memo(context)
        yield _sse({"type": "result", "payload": result.model_dump(mode="json")})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


async def stream_kpis_workflow(
    *,
    db: Session,
    request: KPIExtractionRequest,
) -> AsyncIterator[str]:
    service = StructuredWorkflowService()

    yield _sse({"type": "status", "step": "retrieving", "message": "Retrieving relevant context..."})

    try:
        context = service.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "status", "step": "generating", "message": "Extracting KPIs..."})

    try:
        result = service._execute_kpis(context)
        yield _sse({"type": "result", "payload": result.model_dump(mode="json")})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


async def stream_risks_workflow(
    *,
    db: Session,
    request: RiskExtractionRequest,
) -> AsyncIterator[str]:
    service = StructuredWorkflowService()

    yield _sse({"type": "status", "step": "retrieving", "message": "Retrieving relevant context..."})

    try:
        context = service.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "status", "step": "generating", "message": "Extracting risks..."})

    try:
        result = service._execute_risks(context)
        yield _sse({"type": "result", "payload": result.model_dump(mode="json")})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


async def stream_timeline_workflow(
    *,
    db: Session,
    request: TimelineBuildingRequest,
) -> AsyncIterator[str]:
    service = StructuredWorkflowService()

    yield _sse({"type": "status", "step": "retrieving", "message": "Retrieving relevant context..."})

    try:
        context = service.build_context(
            db=db,
            document_id=request.document_id,
            instruction=request.instruction,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield _sse({"type": "status", "step": "generating", "message": "Building timeline..."})

    try:
        result = service._execute_timeline(context)
        yield _sse({"type": "result", "payload": result.model_dump(mode="json")})
    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})
