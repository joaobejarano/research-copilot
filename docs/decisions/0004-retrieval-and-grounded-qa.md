# ADR 0004: Stage 3 Retrieval and Grounded Q&A

- Status: Accepted
- Date: 2026-03-21

## Context

Stage 3 introduces semantic retrieval and Q&A behavior on top of Stage 2 persisted chunks and embeddings. The stage goal is to provide useful answers while preserving traceability and avoiding unsupported output.

## Decisions

1. Scope retrieval to a single document first
- Retrieval is executed only within `document_id` provided by the request.
- Rationale: keeps relevance behavior predictable while validating retrieval quality against a known evidence set.
- Rationale: reduces complexity in ranking, evaluation, and API semantics before introducing cross-document search.

2. Require citations in grounded answers
- Successful answers include structured citations and inline citation markers.
- Rationale: every answer sentence must be traceable to retrieved chunk evidence.
- Rationale: citation payloads make API responses auditable and easier to verify in tests and UI clients.

3. Prefer explicit `insufficient_evidence` over speculative answers
- When grounding fails, the system returns `status=insufficient_evidence` with a fixed message.
- Rationale: explicit refusal is safer than generating unsupported claims.
- Rationale: this behavior communicates confidence boundaries clearly to users and downstream systems.

4. Defer advanced re-ranking
- Stage 3 uses vector similarity and lightweight lexical sentence selection only.
- Rationale: this delivers a deterministic and testable baseline with low operational complexity.
- Rationale: advanced re-ranking adds tuning and infrastructure cost that is not required to validate Stage 3 goals.

## Consequences

- Stage 3 provides document-scoped retrieval and grounded Q&A with evidence traceability.
- Reliability is prioritized over answer coverage when support is weak.
- Cross-document ranking and advanced ranking strategies remain intentionally deferred.
