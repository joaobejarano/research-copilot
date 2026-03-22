# Research Copilot

Research Copilot is in Stage 4 with a minimal analyst dashboard on top of the Stage 3 document APIs.

## How the Stage 4 dashboard works

The frontend dashboard lives at `GET /documents` in the Next.js app and calls existing backend endpoints directly:

- `GET /documents` for the document list
- `GET /documents/{document_id}` for selected document detail
- `POST /documents/{document_id}/process` to process non-ready documents
- `GET /documents/{document_id}/chunks` for chunk inspection
- `POST /documents/{document_id}/ask` for grounded Q&A

The dashboard keeps state local to the page and provides explicit loading, error, and empty states for each interaction area.

## Required environment variables

### Frontend

Stage 4 frontend requires:

- `NEXT_PUBLIC_API_BASE_URL`
  - Example: `http://127.0.0.1:8000`
  - Used by the frontend API client for all dashboard requests

Set in `frontend/.env.local`:

```bash
cp frontend/.env.example frontend/.env.local
```

### Backend

Backend environment is unchanged from Stage 3 and configured from repository root `.env`:

- `DATABASE_URL` (or `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`)
- `STORAGE_DIR`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `RETRIEVAL_TOP_K`
- `RETRIEVAL_MIN_SIMILARITY`

```bash
cp .env.example .env
```

## Run backend and frontend together

1. Install backend dependencies:
```bash
cd backend
python -m pip install -r requirements-dev.txt
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

3. Start local Postgres (optional if you already have a reachable Postgres):
```bash
docker compose -f infra/docker-compose.yml up -d
```

4. Start backend API:
```bash
cd backend
uvicorn app.main:app --reload
```

5. Start frontend app (new terminal):
```bash
cd frontend
npm run dev
```

Dashboard URL: `http://localhost:3000/documents`  
API docs: `http://127.0.0.1:8000/docs`

## Supported analyst workflows in Stage 4

- view all ingested documents in a table
- select one document and inspect its metadata
- process a selected document and observe status transitions
- inspect document chunks (`chunk_index`, `page_number`, `token_count`, `text`)
- ask grounded questions about one selected document and inspect citations

Still out of scope in Stage 4:

- memo generation UI
- multi-document Q&A UI
- advanced filtering/pagination
- authentication

## Manual dashboard test guide

1. Ensure backend and frontend are running.
2. If no documents exist, upload one via API:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "company_name=Acme Corp" \
  -F "document_type=financial_report" \
  -F "period=2024-Q4" \
  -F "file=@./report.txt;type=text/plain"
```
3. Open `http://localhost:3000/documents`.
4. Verify list and selection behavior:
  - documents table loads
  - selecting a row updates the detail panel
5. Verify processing behavior:
  - for non-ready document, click `Process document`
  - status transition appears
  - detail refreshes and `chunk_count` appears when returned
6. Verify chunks behavior:
  - chunks section loads
  - entries are shown in `chunk_index` order with readable text blocks
7. Verify grounded Q&A behavior:
  - submit a question
  - result shows `question`, `answer`, `status`, `citations`
  - both `answered` and `insufficient_evidence` responses render correctly

## Local checks

Frontend:
```bash
cd frontend
npm run typecheck
npm run build
```

Backend:
```bash
cd backend
pytest -q
```
