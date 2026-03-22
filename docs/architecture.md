# Stage 5 Architecture Additions

This document describes only what Stage 5 adds to the backend.

## Scope Added in Stage 5

- shared structured workflow service for document-scoped research tasks
- reusable LLM provider abstraction for strict JSON outputs
- explicit schemas for:
  - memo generation
  - KPI extraction
  - risk extraction
  - timeline building
- shared evidence/citation structures across all workflow outputs
- document-scoped API endpoints for each workflow

Out of scope in Stage 5:

- frontend workflow UI
- agent orchestration
- workflow persistence
- cross-document workflows

## Backend Components Added

### Workflow schemas (`backend/app/workflows/schemas.py`)

Defines strict Pydantic models:

- shared:
  - `WorkflowCitation`
  - `WorkflowEvidence`
  - base request model with `document_id`, `instruction`, retrieval controls
- memo:
  - `MemoGenerationRequest`, `MemoDraft`, `MemoGenerationOutput`
- KPI:
  - `KPIExtractionRequest`, `KPIItem`, `KPIDraft`, `KPIExtractionOutput`
- risk:
  - `RiskExtractionRequest`, `RiskItem`, `RiskDraft`, `RiskExtractionOutput`
- timeline:
  - `TimelineBuildingRequest`, `TimelineEvent`, `TimelineDraft`, `TimelineBuildingOutput`

### LLM provider abstraction (`backend/app/workflows/llm.py`)

- `StructuredLLMProvider` protocol
- `OpenAIStructuredLLMProvider` implementation using JSON schema response format
- provider factory via `get_llm_provider(...)`

### Workflow orchestration service (`backend/app/workflows/service.py`)

- `StructuredWorkflowService` exposes independent methods:
  - `generate_memo`
  - `extract_kpis`
  - `extract_risks`
  - `build_timeline`
- each method:
  - retrieves evidence chunks for one document
  - returns `insufficient_evidence` when retrieval is weak
  - requests strict structured output from LLM
  - validates cited `C1..Cn` ids against retrieved evidence

### API routes (`backend/app/api/routes/documents.py`)

Stage 5 document-scoped endpoints:

- `POST /documents/{document_id}/memo`
- `POST /documents/{document_id}/extract/kpis`
- `POST /documents/{document_id}/extract/risks`
- `POST /documents/{document_id}/timeline`

Route behavior:

- checks document exists
- requires document status `ready`
- invokes corresponding workflow method
- returns strict structured response with evidence

## Stage 5 Runtime Flow

1. Caller sends workflow request for a single `document_id`.
2. API validates document readiness.
3. Workflow service retrieves top-k relevant chunks.
4. Retrieved chunks are normalized into `evidence.citations` (`C1`, `C2`, ...).
5. LLM returns strict JSON matching workflow schema.
6. Service validates citations referenced by output items.
7. API returns structured result with status:
  - `generated` or `insufficient_evidence` for memo
  - `completed` or `insufficient_evidence` for KPI/risk/timeline

## Test Coverage Added

- schema validation tests for workflow models
- service tests for memo/KPI/risk/timeline behavior
- endpoint tests for:
  - successful structured output
  - insufficient evidence handling
  - `400` when document is not ready
  - `404` for missing document
- integration-style workflow tests with real retrieval and mocked LLM
