# ADR 0003: Stage 2 Processing and Embeddings

- Status: Accepted
- Date: 2026-03-20

## Context

Stage 2 introduces document parsing, chunking, embedding generation, and chunk persistence. The implementation must stay practical for local development while preparing the data foundation needed for Stage 3 retrieval.

## Decisions

1. Keep processing synchronous in Stage 2
- Processing is triggered directly via `POST /documents/{document_id}/process`.
- Rationale: keeps control flow explicit and easy to validate locally.
- Rationale: avoids introducing worker orchestration before retrieval requirements are in place.

2. Keep embeddings local in Stage 2
- Use a local `sentence-transformers` provider as the default embedding backend.
- Rationale: enables offline-ish local development after model download and avoids external API dependencies for core processing validation.
- Rationale: keeps provider integration simple while preserving a replaceable provider interface.

3. Introduce pgvector in Stage 2
- Persist chunk embeddings in `document_chunks.embedding` as vector data.
- Rationale: Stage 2 is the first stage where embeddings are generated and stored.
- Rationale: introducing pgvector now validates the storage shape and schema needed for upcoming retrieval work.

4. Defer retrieval to Stage 3
- Stage 2 stops at processing and chunk inspection.
- Rationale: retrieval requires ranking/query semantics and product behavior not required for validating the processing pipeline.
- Rationale: separating processing from retrieval keeps Stage 2 narrow, testable, and lower risk.

## Consequences

- Stage 2 has a complete synchronous processing path from stored file to persisted chunks with vectors.
- Operational complexity remains low for local iteration.
- Retrieval behavior is intentionally unavailable until Stage 3.
