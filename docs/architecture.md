# Stage 2 Architecture Additions

This document describes only what Stage 2 adds on top of Stage 1 ingestion.

## Scope Added in Stage 2

- synchronous document processing endpoint
- parsing for `.txt` and `.pdf`
- deterministic chunking with overlap
- local embedding generation
- chunk persistence in pgvector-backed `document_chunks`
- chunk inspection endpoint

Still out of scope in Stage 2:
- retrieval and semantic search
- Q&A workflows
- background workers

## Components Added

### API additions (`backend/app/api/routes/documents.py`)

- `POST /documents/{document_id}/process`
  - synchronous processing entrypoint
  - status flow: `uploaded -> processing -> ready` or `uploaded -> processing -> failed`
- `GET /documents/{document_id}/chunks`
  - returns chunk inspection payload ordered by `chunk_index`
  - excludes raw embedding vectors from response
  - includes `embedding_dimension` metadata

### Ingestion modules (`backend/app/ingestion/`)

- `parsing.py`
  - `parse_txt_file` and `parse_pdf_file`
  - `parse_document` dispatch by file extension
- `chunking.py`
  - deterministic token-based chunking with `CHUNK_SIZE` and `CHUNK_OVERLAP`
  - per-chunk `token_count` approximation
- `embeddings.py`
  - replaceable embedding provider protocol
  - Stage 2 local provider using `sentence-transformers`
  - strict embedding dimension validation
- `processing.py`
  - orchestrates parse -> chunk -> embed -> persist
  - supports safe reprocessing by replacing existing chunks for a document

### Database additions

- `document_chunks` table (`backend/app/db/models/document_chunk.py`) with:
  - `document_id`, `chunk_index`, `page_number`, `text`, `token_count`, `embedding`, `created_at`
- `embedding` column stored as pgvector (`VECTOR(EMBEDDING_DIMENSION)`)
- startup ensures `vector` extension exists before table creation

### Infrastructure additions

- local Postgres image updated to `pgvector/pgvector:pg16` (`infra/docker-compose.yml`)

## Stage 2 Processing Flow

1. Client uploads document in Stage 1 flow (`status=uploaded`).
2. Client calls `POST /documents/{document_id}/process`.
3. API sets status to `processing`.
4. Processing pipeline loads file from local storage and parses `.txt` or `.pdf`.
5. Chunker creates deterministic chunks using configured size and overlap.
6. Local embedder generates one vector per chunk and validates dimension.
7. Existing chunks for that document are deleted and replaced with new persisted chunks.
8. API sets status to `ready` on success, or `failed` on exception.

## Data Boundaries in Stage 2

- Chunk inspection returns text and metadata for debugging and validation.
- Raw embedding vectors remain persisted in DB and are not returned by default.
