# Research Copilot

Research Copilot is in Stage 6.

Stage 6 adds a backend reliability layer for grounded outputs:

- citation verification for grounded Q&A
- confidence scoring and explicit gate decisions
- one constrained, document-scoped research agent
- fail-safe output gating (`passed`, `needs_review`, `blocked`)

## How Stage 6 Reliability Works

Stage 6 reliability runs in two places:

1. Grounded Q&A verification
- `POST /documents/{document_id}/verify/ask`
- The system validates citation presence, document match, and excerpt grounding.
- It then computes confidence signals and a gate decision.

2. Constrained research agent
- `POST /documents/{document_id}/agent`
- The agent selects from existing tools only:
  - `ask`
  - `memo`
  - `extract_kpis`
  - `extract_risks`
  - `build_timeline`
- The agent records a deterministic trace, computes confidence, decides gate status, and withholds final outputs unless the gate passes.

## Status Meanings

Agent response status is explicit:

- `passed`: verification and confidence checks allow execution; outputs are returned.
- `needs_review`: confidence is not high enough (or verification is inconclusive); outputs are withheld and reasons are returned.
- `blocked`: verification failed or execution cannot proceed safely (for example, document not ready); outputs are withheld and reasons are returned.

## Required Environment Variables

Create backend environment:

```bash
cp .env.example .env
```

Stage 6 reliability variables:

- `CONFIDENCE_PASS_THRESHOLD` (default: `0.75`)
- `CONFIDENCE_REVIEW_THRESHOLD` (default: `0.50`)
- `ENABLE_CONFIDENCE_GATING` (default: `true`)
- `MAX_AGENT_TOOL_CALLS` (default: `20`)

Also required for workflows/LLM:

- `OPENAI_API_KEY`
- `LLM_PROVIDER` (default: `openai`)
- `LLM_MODEL` (example: `gpt-4.1-mini`)
- `MAX_WORKFLOW_CITATIONS`
- `MAX_WORKFLOW_ITEMS`

Also required for ingestion/retrieval:

- `DATABASE_URL` (or `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`)
- `STORAGE_DIR`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `RETRIEVAL_TOP_K`
- `RETRIEVAL_MIN_SIMILARITY`

If you run the Stage 4 frontend dashboard:

- `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`

## Run Backend

1. Install backend dependencies:

```bash
cd backend
python -m pip install -r requirements-dev.txt
```

2. Start local Postgres (if needed):

```bash
docker compose -f infra/docker-compose.yml up -d
```

3. Start backend:

```bash
cd backend
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Use the Verification Endpoint

Verify a grounded answer with reliability assessment:

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/verify/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What happened to revenue in Q4?",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

The response includes:

- `verification`
- `confidence`
- `gate_decision`
- `issues`

## Use the Agent Endpoint

Run the constrained agent on one document:

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Extract KPIs and risks, then answer what changed in Q4.",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

The response includes:

- `instruction`
- `status`
- `selected_tools`
- `trace`
- `outputs`
- `outputs_withheld`
- `decision_reasons`
- `confidence`
- `gate_decision`

Note: the document must exist. If it is not `ready`, agent execution is blocked.

## How to Run Tests

Run all backend tests:

```bash
pytest -q backend/tests
```

Run reliability-focused tests:

```bash
pytest -q backend/tests/test_reliability_*.py backend/tests/test_documents_agent.py backend/tests/test_documents_verify_ask.py
```
