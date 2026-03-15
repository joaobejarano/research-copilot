# ADR 0001: Stage 0 Bootstrap Stack

- Status: Accepted
- Date: 2026-03-14

## Context

Stage 0 requires a minimal, testable local baseline with clear separation between application code and agent workflow tooling.

## Decisions

1. FastAPI for backend
- Use FastAPI as the backend framework for the initial API service.
- Rationale: simple setup, clear route definitions, and good fit for a minimal HTTP-first bootstrap.

2. Next.js for frontend
- Use Next.js with TypeScript for the initial web UI.
- Rationale: minimal setup for a single-page landing screen with an established local development workflow.

3. Postgres as the initial database
- Use Postgres as the only local infrastructure service in Stage 0.
- Rationale: standard relational database baseline for local development, kept independent from runtime features at this stage.

4. AGENTS and skills are separate from application code
- Keep `.agents/` and skill instructions separate from `backend/`, `frontend/`, and `infra/`.
- Rationale: preserves clean boundaries between delivery tooling and application runtime code.

5. MCP is deferred to its own future stage
- Do not include MCP code or MCP integration in Stage 0.
- Rationale: maintain strict scope control and introduce MCP only in the dedicated stage.

## Consequences

- Stage 0 remains small, runnable, and easy to validate locally.
- Some capabilities are intentionally absent until later stages.
