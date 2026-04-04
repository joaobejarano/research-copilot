# AGENTS.md

## Mission
Build Research Copilot incrementally, one integrable change at a time.

## Current project reality (Stage 9 baseline)
- `backend/`: FastAPI backend for ingestion, retrieval, grounded workflows, reliability, and feedback APIs.
- `frontend/`: Next.js + TypeScript analyst dashboard with lightweight review flow.
- `evals/`: local deterministic eval datasets, runner, report generation, and feedback export utilities.
- `mcp_server/`: separate FastMCP server that exposes document-scoped tools by calling existing backend capabilities.
- `docs/`: stage architecture notes and ADRs.

## Core operating rules
- Implement only the scope explicitly requested in the current task.
- Do not add future-stage behavior unless requested.
- Prefer minimal, testable changes over broad refactors.
- Do not modify unrelated modules.
- Keep backend, frontend, evals, and MCP changes isolated unless the task requires cross-layer integration.
- Stop once the requested deliverable is complete.

## Architecture guardrails
- Keep MCP server separate from the FastAPI backend process.
- Reuse existing backend workflows/endpoints; do not duplicate business logic in MCP or other layers.
- Keep workflows and MCP tools document-scoped unless explicitly requested otherwise.
- Avoid premature architecture additions (workers, queues, external integrations, auth redesigns, complex client state).
- Prefer explicit, readable structures over speculative abstractions.

## Implementation workflow
1. Confirm task scope and target modules.
2. Make the smallest viable code change set.
3. Add or update deterministic tests for changed behavior.
4. Update docs when contracts, commands, or architecture notes change.
5. Run relevant checks before handoff.

## Testing before handoff
- Run the tests that cover the changed area:
  - backend: `.venv/bin/pytest -q backend/tests`
  - MCP server: `.venv/bin/pytest -q mcp_server/tests`
  - evals: `.venv/bin/pytest -q evals/tests`
  - frontend (if changed): `cd frontend && npm run typecheck`
- Prefer targeted tests first, then broader suites when practical.
- If a check cannot be run, explicitly report the gap and why.

## Documentation update rules
- Update `README.md` for developer-facing run/test/usage changes.
- Update `docs/architecture.md` for stage-specific architecture additions only.
- Add or update ADRs in `docs/decisions/` for meaningful design decisions.
- Do not document unimplemented functionality as if it exists.

## Handoff format
Every task handoff must include:
- files changed
- how to run
- how to test
- expected result
- suggested commit message
