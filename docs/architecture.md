# Stage 1 Architecture: Document Ingestion

## Scope

Stage 1 implements minimal document ingestion in the backend:
- upload a file and persist metadata
- store files on local disk
- read metadata with list and by-id endpoints

Out of scope in Stage 1:
- document parsing
- embeddings
- background workers
- filtering and pagination for document listing
- frontend ingestion UI

## Components

### API layer (`backend/app/api/routes/documents.py`)
- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`

Routes are intentionally thin and operate directly with SQLAlchemy sessions.

### Persistence layer (`backend/app/db/models/document.py`)
- Single `documents` table with fields:
  - `id`
  - `company_name`
  - `document_type`
  - `period`
  - `source_filename`
  - `storage_path`
  - `status`
  - `created_at`

### Storage
- Uploaded files are written to local filesystem under `STORAGE_DIR`.
- Stored path format:
  - `<sanitized_company>/<sanitized_document_type>/<sanitized_period>/<id>.<ext>`
- `storage_path` persisted in DB is relative to `STORAGE_DIR`.

### Runtime dependencies
- FastAPI for HTTP endpoints
- SQLAlchemy for DB access
- Postgres as default database target

## Request flows

### Upload flow (`POST /documents/upload`)
1. Validate multipart request and file extension.
2. Insert `documents` row with temporary `storage_path` and status `uploaded`.
3. Write file to local storage path derived from metadata and generated document id.
4. Update row with final relative `storage_path`.
5. Commit transaction and return metadata response.

### Read flow (`GET /documents`)
1. Query `documents` ordered by ascending `id`.
2. Return metadata list response.

### Read flow (`GET /documents/{document_id}`)
1. Lookup row by primary key.
2. Return metadata when found.
3. Return `404` when not found.

## Data boundaries

- Stage 1 responses are metadata-only.
- No parsed content is returned by ingestion endpoints.
