# Research Copilot

Research Copilot is in Stage 3 with document-scoped semantic retrieval and grounded Q&A.

Current Stage 3 implementation includes:
- document upload and metadata endpoints
- synchronous processing endpoint (`POST /documents/{document_id}/process`)
- parsing support for `.txt` and `.pdf`
- deterministic chunking with configurable size and overlap
- local embedding generation using `sentence-transformers`
- chunk persistence in `document_chunks` with pgvector-compatible embeddings
- chunk inspection endpoint (`GET /documents/{document_id}/chunks`)
- semantic retrieval endpoint (`POST /documents/{document_id}/retrieve`)
- grounded Q&A endpoint (`POST /documents/{document_id}/ask`) with citations

## How Stage 3 retrieval works

1. The client sends a question to `POST /documents/{document_id}/retrieve`.
2. The backend generates an embedding for the question.
3. Retrieval is scoped to the requested `document_id` only.
4. Chunks are ranked by vector similarity and filtered by `min_similarity`.
5. Up to `top_k` chunks are returned with:
- `chunk_index`
- `page_number`
- `text`
- `token_count`
- `similarity`

Notes:
- Chunks without embeddings are skipped.
- In PostgreSQL, ranking uses pgvector distance.
- In non-PostgreSQL test/local fallback paths, ranking uses cosine similarity in Python.

## Required environment variables

Stage 3 requires:

- `DATABASE_URL`
  - Example: `postgresql+psycopg://research_copilot:research_copilot@localhost:5432/research_copilot`
- `STORAGE_DIR`
  - Example: `storage/documents` (relative to repository root) or an absolute path
- `CHUNK_SIZE`
  - Example: `800`
- `CHUNK_OVERLAP`
  - Example: `120`
- `EMBEDDING_PROVIDER`
  - Stage 3 value: `local`
- `EMBEDDING_MODEL`
  - Example: `sentence-transformers/all-MiniLM-L6-v2`
- `EMBEDDING_DIMENSION`
  - Example: `384`
- `RETRIEVAL_TOP_K`
  - Default: `5`
- `RETRIEVAL_MIN_SIMILARITY`
  - Default: `0.2`

If `DATABASE_URL` is not set, backend builds one from:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## Run backend locally

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

## Upload and process a document

1. Upload:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "company_name=Acme Corp" \
  -F "document_type=financial_report" \
  -F "period=2024-Q4" \
  -F "file=@./report.txt;type=text/plain"
```

2. Process:
```bash
curl -X POST "http://127.0.0.1:8000/documents/1/process"
```

Example response:
```json
{
  "document_id": 1,
  "status": "ready",
  "chunk_count": 3
}
```

## Ask a grounded question

Request:
```bash
curl -X POST "http://127.0.0.1:8000/documents/1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What happened to revenue in Q4?",
    "top_k": 5,
    "min_similarity": 0.2
  }'
```

Example successful grounded response:
```json
{
  "question": "What happened to revenue in Q4?",
  "answer": "Revenue increased 12 percent in Q4. [C1]",
  "status": "answered",
  "citations": [
    {
      "citation_id": "C1",
      "rank": 1,
      "document_id": 1,
      "chunk_index": 0,
      "page_number": 1,
      "text_excerpt": "Revenue increased 12 percent in Q4 ...",
      "retrieval_score": 0.92
    }
  ]
}
```

## What `insufficient_evidence` means

`status: "insufficient_evidence"` means the system could not produce a grounded answer from retrieved context.

This happens when:
- no chunks pass retrieval threshold (`citations` is empty), or
- chunks are retrieved but no sentence has enough lexical support for the question (`citations` contains top retrieved evidence snippets).

In both cases, the API returns:
- `answer`: `"Insufficient evidence to answer the question from retrieved context."`
- `status`: `"insufficient_evidence"`

## Run tests

All backend tests:
```bash
cd backend
pytest -q
```

Stage 3 retrieval and grounded Q&A tests:
```bash
cd backend
pytest -q \
  tests/test_retrieval_service.py \
  tests/test_documents_retrieve.py \
  tests/test_documents_ask.py
```
