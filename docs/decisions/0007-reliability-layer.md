# ADR 0007: Stage 6 Reliability Layer

- Status: Accepted
- Date: 2026-04-03

## Context

Stage 5 introduced structured document-scoped workflows (`memo`, `extract_kpis`, `extract_risks`, `timeline`) and grounded Q&A. Stage 6 needs a practical safety layer before wider orchestration:

- verify that grounded outputs are actually supported by citations
- make confidence and execution gating explicit in API contracts
- add orchestration while keeping behavior deterministic and auditable

The project is still early-stage. Reliability must improve without introducing high operational complexity.

## Decisions

1. Prefer one constrained agent over multi-agent orchestration in Stage 6
- Introduce a single document-scoped constrained agent that can only call existing internal tools.
- Rationale: a single orchestrator is easier to reason about, test, and debug.
- Rationale: multi-agent behavior introduces non-trivial coordination/failure modes not required for Stage 6 goals.
- Rationale: constrained tool selection keeps execution traceable and cost/latency bounded.

2. Introduce citation verification now
- Add verification checks for citation existence, document ownership, and excerpt grounding.
- Add numeric-claim support checks for grounded Q&A.
- Rationale: Stage 5 outputs already depend on citations; verification is the minimum next step for safety.
- Rationale: explicit citation checks provide immediate, deterministic signals for trust and failure handling.

3. Make confidence gating explicit
- Keep confidence bands and gate decisions (`pass`, `review`, `block`) in the API response.
- Map agent response statuses explicitly to `passed`, `needs_review`, and `blocked`.
- Withhold final agent outputs unless gate decision is `pass`.
- Rationale: explicit gating is safer than implicit heuristics and easier for downstream consumers to enforce.
- Rationale: returning reasons for review/block keeps decisions explainable and actionable.

4. Defer human review workflow to next stage
- Stage 6 returns review/block reasons but does not add reviewer UI or workflow execution tooling.
- Rationale: current priority is backend safety primitives and deterministic contracts.
- Rationale: adding review operations now would expand scope beyond Stage 6 and couple backend to unfinished product decisions.

## Consequences

- Stage 6 improves grounded-output safety without introducing multi-agent complexity.
- API consumers can programmatically enforce reliability outcomes.
- Manual review remains a clear next-step integration point for the following stage.
