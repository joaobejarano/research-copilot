# Research Copilot

Research Copilot is in Stage 1 with a minimal document ingestion backend.

Current Stage 1 implementation includes:
- FastAPI endpoints to upload documents and persist metadata
- local filesystem storage for uploaded files
- metadata read endpoints (`GET /documents`, `GET /documents/{document_id}`)
- backend tests for upload and metadata reads

## Stage 1 ingestion flow

1. Client uploads a document using `POST /documents/upload` with:
   - `company_name` (form field)
   - `document_type` (form field)
   - `period` (form field)
   - `file` (multipart file)
2. Backend validates file extension (`.pdf`, `.txt`, `.doc`, `.docx`).
3. Backend creates a `documents` row with status `uploaded`.
4. Backend stores the file under `STORAGE_DIR/<company>/<document_type>/<period>/<id>.<ext>`.
5. Backend persists metadata including relative `storage_path`.
6. Clients can read metadata using:
   - `GET /documents`
   - `GET /documents/{document_id}`

The API returns metadata only. Parsed content is not part of Stage 1.

## Repository structure

```text
backend/   FastAPI application and backend tests
frontend/  Next.js (TypeScript) application
infra/     Local infrastructure (docker-compose)
docs/      Project documentation and architecture decisions
.agents/   Agent workflows and skills (kept separate from app code)
```

## Required environment variables

Stage 1 ingestion needs a database connection and a storage directory:

- `DATABASE_URL`
  - Example: `postgresql+psycopg://research_copilot:research_copilot@localhost:5432/research_copilot`
- `STORAGE_DIR`
  - Example: `storage/documents` (relative to repository root) or an absolute path

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

## Upload a file with curl

```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "company_name=Acme Corp" \
  -F "document_type=financial_report" \
  -F "period=2024-Q4" \
  -F "file=@./report.pdf;type=application/pdf"
```

## List documents

```bash
curl "http://127.0.0.1:8000/documents"
```

## Fetch a document by id

```bash
curl "http://127.0.0.1:8000/documents/1"
```

## Run tests

```bash
cd backend
pytest -q
```
