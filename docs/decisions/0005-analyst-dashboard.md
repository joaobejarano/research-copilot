# ADR 0005: Stage 4 Minimal Analyst Dashboard

- Status: Accepted
- Date: 2026-03-22

## Context

Stage 4 introduces the first analyst-facing dashboard. Stage 3 already provides the backend capabilities (document detail, processing, chunk retrieval, and grounded Q&A), but there is no integrated UI flow for analysts to operate on one document end-to-end.

The stage goal is to deliver a practical, low-risk dashboard that validates real analyst workflows without introducing future-stage complexity.

## Decisions

1. Start with a minimal dashboard first
- Implement one explicit page (`/documents`) with clear sections and local state.
- Rationale: reduces integration risk and shortens feedback loops while frontend/backend contracts stabilize.
- Rationale: keeps Stage 4 testable and production-oriented without introducing unnecessary abstractions.

2. Make document detail the main interaction surface
- Use selected document detail as the anchor for processing, chunk inspection, and grounded Q&A.
- Rationale: all current backend operations are document-scoped; centering detail reflects existing API boundaries.
- Rationale: keeps analyst flow explicit: select document -> inspect state -> process -> inspect evidence -> ask questions.

3. Defer memo UI
- Do not include memo authoring or memo generation UI in Stage 4.
- Rationale: memo workflows depend on higher-level orchestration and product decisions not required to validate current dashboard behavior.
- Rationale: separating memo UX avoids coupling Stage 4 with future-stage business workflows.

4. Defer advanced filtering and authentication
- Keep list behavior simple (no advanced filtering/pagination) and no auth layer yet.
- Rationale: current stage objective is validating core analyst interactions, not access control or large-list optimization.
- Rationale: both filtering complexity and auth requirements should be introduced with concrete scale/security constraints in later stages.

## Consequences

- Stage 4 provides a usable analyst dashboard with explicit document workflows and evidence visibility.
- Operational complexity remains low (no design system dependency, no global state framework, no auth stack).
- Memo UX, advanced list controls, and authenticated multi-user concerns remain intentionally deferred to later stages.
