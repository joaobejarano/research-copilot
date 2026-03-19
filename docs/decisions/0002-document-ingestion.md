# ADR 0002: Stage 1 Document Ingestion

- Status: Accepted
- Date: 2026-03-19

## Context

Stage 1 needs a minimal, testable ingestion workflow that persists uploaded documents and exposes metadata read endpoints. The goal is to deliver a stable baseline without introducing later-stage complexity.

## Decisions

1. Store uploaded files locally in Stage 1
- Files are written under `STORAGE_DIR` on the local filesystem.
- Rationale: lowest operational complexity for local development and deterministic tests.
- Rationale: keeps ingestion implementation small while metadata persistence is validated.

2. Defer parsing to a later stage
- Stage 1 ingestion stores raw files and metadata only.
- Rationale: parsing introduces format-specific behavior and error handling that is not required for the first ingest baseline.
- Rationale: separating ingestion from parsing keeps Stage 1 scope tight and easier to verify.

3. Defer Alembic migrations
- Stage 1 creates tables directly from SQLAlchemy models at startup.
- Rationale: schema is still small and evolving quickly during bootstrap.
- Rationale: adding migration workflow now would increase setup overhead before stable schema pressure exists.

4. Keep a single initial status value: `uploaded`
- New documents are persisted with `status="uploaded"`.
- Rationale: Stage 1 has no parser or downstream pipeline states yet.
- Rationale: a simple explicit status supports current behavior without premature workflow modeling.

## Consequences

- Stage 1 remains small and practical to run locally with straightforward tests.
- The system intentionally lacks parsing pipeline states and migration history until later stages.
