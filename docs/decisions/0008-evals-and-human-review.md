# ADR 0008: Stage 7 Evals and Human Review

- Status: Accepted
- Date: 2026-04-03

## Context

By the end of Stage 6, the project had reliability primitives (verification, confidence, gating) and constrained orchestration. Stage 7 needs a practical quality loop that is explicit, inspectable, and lightweight:

- evaluate grounded workflow behavior consistently
- collect human feedback on real outputs
- convert review signals into follow-up quality work

The project still prioritizes local iteration speed and clear operational behavior.

## Decisions

1. Evals are explicit and dataset-driven instead of ad hoc
- Define eval inputs through maintainable fixtures and case files.
- Execute existing workflows through a shared local runner.
- Generate concrete reports for each run.
- Rationale: ad hoc spot checks do not provide repeatable baselines or reliable comparisons across changes.
- Rationale: explicit datasets make failures reproducible and easier to triage.

2. Deterministic metrics are introduced first
- Start with explicit deterministic metrics (`schema_adherence`, `abstention_correctness`, `citation_presence`, `citation_accuracy`).
- Keep metric calculations directly inspectable in code.
- Rationale: deterministic checks provide stable signals during early iteration.
- Rationale: introducing subjective/LLM-judge signals first would increase ambiguity and debugging cost.

3. Human review is lightweight first
- Add minimal backend feedback capture and a simple dashboard review panel.
- Require reason for negative feedback to improve downstream usefulness.
- Defer advanced review workflow management.
- Rationale: Stage 7 needs practical collection of high-value review signals without adding large workflow complexity.
- Rationale: lightweight review enables adoption before broader product decisions are finalized.

4. Feedback informs future quality improvement through explicit export
- Add a local script to transform stored feedback into follow-up eval candidate cases.
- Prioritize negative feedback rows as follow-up opportunities.
- Keep final case curation manual and explicit in Stage 7.
- Rationale: this creates a concrete bridge from production-like review signals to improved eval coverage.
- Rationale: avoids premature active-learning pipeline complexity while still closing the quality loop.

## Consequences

- Stage 7 establishes a repeatable evaluation baseline for grounded workflows.
- Human feedback becomes structured and queryable rather than implicit.
- The team can iterate on quality by promoting feedback-derived candidates into maintained eval datasets.
- More advanced automation remains intentionally deferred beyond Stage 7.
