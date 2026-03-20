# Research Copilot

Research Copilot is in Stage 2 with synchronous document processing.

Current Stage 2 implementation includes:
- document upload and metadata endpoints
- synchronous processing endpoint (`POST /documents/{document_id}/process`)
- parsing support for `.txt` and `.pdf`
- deterministic chunking with configurable size and overlap
- local embedding generation using `sentence-transformers`
- chunk persistence in `document_chunks` with pgvector embeddings
- chunk inspection endpoint (`GET /documents/{document_id}/chunks`)

## How Stage 2 processing works

1. Upload a document with `POST /documents/upload` (status starts as `uploaded`).
2. Trigger processing with `POST /documents/{document_id}/process`.
3. During processing:
- status changes to `processing`
- stored file is loaded from `STORAGE_DIR`
- parser reads `.txt` or `.pdf`
- chunker splits content using `CHUNK_SIZE` and `CHUNK_OVERLAP`
- local embedding provider generates one vector per chunk
- chunks are persisted in `document_chunks` (safe for reprocessing)
4. On success, status changes to `ready`.
5. On failure, status changes to `failed`.
6. Inspect chunks with `GET /documents/{document_id}/chunks` (no raw embedding vector in response).

Note: the first embedding run may download the configured sentence-transformers model.

## Repository structure

```text
backend/   FastAPI application and backend tests
frontend/  Next.js (TypeScript) application
infra/     Local infrastructure (docker-compose)
docs/      Project documentation and architecture decisions
.agents/   Agent workflows and skills (kept separate from app code)
```

## Required environment variables

Stage 2 requires:

- `DATABASE_URL`
  - Example: `postgresql+psycopg://research_copilot:research_copilot@localhost:5432/research_copilot`
- `STORAGE_DIR`
  - Example: `storage/documents` (relative to repository root) or an absolute path
- `CHUNK_SIZE`
  - Example: `800`
- `CHUNK_OVERLAP`
  - Example: `120`
- `EMBEDDING_PROVIDER`
  - Stage 2 value: `local`
- `EMBEDDING_MODEL`
  - Example: `sentence-transformers/all-MiniLM-L6-v2`
- `EMBEDDING_DIMENSION`
  - Example: `384`

If `DATABASE_URL` is not set, backend builds one from:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## Run backend locally (Stage 2)

1. Install dependencies:
```bash
cd backend
python -m pip install -r requirements-dev.txt
```

2. Configure environment (from repository root):
```bash
cp .env.example .env
```

3. Start local Postgres (optional if you already have a reachable Postgres):
```bash
docker compose -f infra/docker-compose.yml up -d
```

4. Start API:
```bash
cd backend
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Upload a document

```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "company_name=Acme Corp" \
  -F "document_type=financial_report" \
  -F "period=2024-Q4" \
  -F "file=@./report.txt;type=text/plain"
```

## Process a document

```bash
curl -X POST "http://127.0.0.1:8000/documents/1/process"
```

Example successful response:
```json
{
  "document_id": 1,
  "status": "ready",
  "chunk_count": 3
}
```

## Inspect chunks

```bash
curl "http://127.0.0.1:8000/documents/1/chunks"
```

## Run tests

```bash
cd backend
pytest -q
```

Stage 2-focused tests:
```bash
cd backend
pytest -q \
  tests/test_parsing.py \
  tests/test_chunking.py \
  tests/test_embeddings.py \
  tests/test_processing.py \
  tests/test_documents_process.py \
  tests/test_documents_chunks.py
```
