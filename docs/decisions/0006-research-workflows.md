# ADR 0006: Stage 5 Structured Research Workflows

- Status: Accepted
- Date: 2026-03-22

## Context

Stage 5 adds backend workflows for analyst outputs built from retrieved document chunks:

- memo generation
- KPI extraction
- risk extraction
- timeline building

The project needs outputs that are predictable for downstream use, grounded in source evidence, and safe to run per document without introducing cross-document complexity.

## Decisions

1. Use structured outputs instead of free-form text
- All workflow outputs are strict JSON validated by explicit Pydantic schemas.
- Rationale: structured outputs are stable for API clients and tests.
- Rationale: explicit schemas reduce ambiguity and simplify failure handling.
- Rationale: strict typing limits format drift across model/provider changes.

2. Keep memo, KPI, risk, and timeline as separate workflows
- Each workflow has its own request and response schema and endpoint.
- Rationale: each task has different shape, acceptance criteria, and failure modes.
- Rationale: independent workflows are easier to test and evolve without coupling.
- Rationale: separation keeps route and service logic explicit in this stage.

3. Keep everything document-scoped in Stage 5
- Every workflow request is anchored to one `document_id`.
- Rationale: Stage 5 builds on existing single-document retrieval/chunk infrastructure.
- Rationale: document scope keeps evidence mapping direct and auditable.
- Rationale: avoids premature multi-document orchestration complexity.

4. Require evidence on workflow outputs
- Responses include shared `evidence.citations` and workflow items reference citation ids.
- Rationale: analysts need traceability for claims and extracted items.
- Rationale: evidence requirements enforce grounded generation behavior.
- Rationale: explicit citations allow deterministic validation in tests and APIs.

## Consequences

- Stage 5 provides practical, testable structured research workflows without frontend or orchestration expansion.
- API consumers can reliably parse outputs and inspect evidence provenance.
- Cross-document workflows and agent orchestration remain deferred to later stages.
