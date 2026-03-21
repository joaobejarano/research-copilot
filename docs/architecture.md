# Stage 3 Architecture Additions

This document describes only what Stage 3 adds on top of Stage 2 processing and embeddings.

## Scope Added in Stage 3

- document-scoped semantic retrieval API
- grounded Q&A API with structured citations
- insufficient-evidence response path to prevent unsupported answers

Still out of scope in Stage 3:
- cross-document retrieval
- advanced re-ranking pipelines
- memo generation workflows
- agent orchestration

## API Additions (`backend/app/api/routes/documents.py`)

- `POST /documents/{document_id}/retrieve`
  - request: `question`, optional `top_k`, optional `min_similarity`
  - response: ranked chunk list with `similarity`
  - behavior: retrieval is restricted to the specified document
- `POST /documents/{document_id}/ask`
  - request: `question`, optional `top_k`, optional `min_similarity`
  - response: `question`, `answer`, `status`, `citations`
  - status values:
    - `answered`
    - `insufficient_evidence`

## Retrieval Component (`backend/app/retrieval/service.py`)

- Generates a single query embedding from the incoming question.
- Validates retrieval parameters:
  - `top_k > 0`
  - `-1 <= min_similarity <= 1`
- Uses pgvector ranking in PostgreSQL (`embedding <=> query` distance).
- Uses deterministic Python cosine fallback for non-PostgreSQL environments.
- Filters out chunks with null embeddings.
- Returns ranked `RetrievedChunk` records with:
  - `chunk_index`
  - `page_number`
  - `text`
  - `token_count`
  - `similarity`

## Grounded Q&A Component (`backend/app/qa/service.py`)

- Calls retrieval first using the same `top_k` and `min_similarity`.
- Selects answer sentences only from retrieved chunk text.
- Requires lexical overlap between question keywords and candidate sentences.
- Builds citations as structured evidence payload:
  - `citation_id`, `rank`, `document_id`, `chunk_index`, `page_number`, `text_excerpt`, `retrieval_score`
- Appends inline citation references (`[C1]`, `[C2]`) to grounded answers.

## Insufficient-Evidence Path

- If retrieval returns no chunks:
  - `status = insufficient_evidence`
  - `citations = []`
- If retrieval returns chunks but none can ground an answer sentence:
  - `status = insufficient_evidence`
  - returns up to three top retrieved chunks as citations
- In both cases, answer text is:
  - `Insufficient evidence to answer the question from retrieved context.`

## Stage 3 Runtime Flow

1. Client uploads and processes a document (Stage 1-2 flow).
2. Client asks retrieval or Q&A against one document id.
3. System embeds the question and ranks persisted chunks for that document.
4. For Q&A, system either:
- returns grounded sentences with citations (`answered`), or
- returns `insufficient_evidence` with explicit evidence handling.
