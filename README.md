# Research Copilot

Research Copilot is in Stage 5. Stage 4 provides a minimal analyst dashboard, and Stage 5 adds structured, document-scoped research workflows in the backend.

## How Stage 5 research workflows work

Stage 5 introduces strict JSON workflows that use retrieved chunks from one processed document:

- `POST /documents/{document_id}/memo`
- `POST /documents/{document_id}/extract/kpis`
- `POST /documents/{document_id}/extract/risks`
- `POST /documents/{document_id}/timeline`

All outputs are:

- document-scoped
- schema-validated
- grounded with `evidence.citations`
- returned as `insufficient_evidence` when context is weak

## Required environment variables

Create backend environment:

```bash
cp .env.example .env
```

Stage 5 backend variables:

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

## Run backend (and optional frontend)

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

Optional Stage 4 dashboard:

```bash
cd frontend
npm install
npm run dev
```

API docs: `http://127.0.0.1:8000/docs`  
Dashboard: `http://localhost:3000/documents`

## How to generate a memo

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/memo" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Generate a grounded investment memo.",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

## How to extract KPIs

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/extract/kpis" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Extract decision-relevant KPIs.",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

## How to extract risks

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/extract/risks" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Extract material risks.",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

## How to build a timeline

```bash
curl -X POST "http://127.0.0.1:8000/documents/{document_id}/timeline" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Build a timeline of key events.",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

Note: document must exist and be `ready` (processed) before these endpoints run.

## How to run tests

Run all backend tests:

```bash
pytest -q backend/tests
```

Run only workflow tests:

```bash
pytest -q backend/tests/test_workflow_*.py backend/tests/test_documents_memo.py backend/tests/test_documents_workflows.py
```
