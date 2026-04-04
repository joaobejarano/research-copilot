# ADR 0009: Stage 8 MCP Server

- Status: Accepted
- Date: 2026-04-04

## Context

By the end of Stage 7, Research Copilot had backend workflows, reliability controls, evals, and feedback capture. Stage 8 introduces MCP access without changing the core backend architecture or duplicating workflow logic.

The first MCP increment must be practical, inspectable, and low-risk:

- expose useful capabilities quickly to MCP clients
- preserve grounded behavior and existing reliability boundaries
- avoid introducing parallel business logic paths

## Decisions

1. The MCP server is a separate process from the main backend
- Implement MCP in `mcp_server/` with its own bootstrap and runtime settings.
- Keep FastAPI backend as the single business-logic API surface.
- Rationale: clear process boundary reduces coupling and keeps MCP transport/runtime concerns isolated.
- Rationale: backend remains the source of truth for workflow behavior and data contracts.

2. Read-only tools are introduced before action tools
- Start with document discovery and chunk inspection primitives.
- Add action tools only after foundational visibility is in place.
- Rationale: read-only inspection gives safe observability and easier debugging during MCP bring-up.
- Rationale: staged rollout lowers integration risk while validating client/tool ergonomics.

3. MCP tools reuse existing workflows instead of duplicating logic
- MCP tools call existing backend endpoints for ask/memo/risk extraction.
- No parallel workflow implementation is added in MCP.
- Rationale: one implementation path prevents behavior drift and reduces maintenance overhead.
- Rationale: existing grounded/reliability behavior is preserved automatically.

4. Initial MCP scope remains document-scoped
- Every Stage 8 tool requires or operates on a single `document_id` context.
- No cross-document orchestration is introduced.
- Rationale: document scope keeps contracts explicit and limits early complexity.
- Rationale: this aligns with current grounded workflow assumptions and existing API boundaries.

## Consequences

- MCP capabilities are available locally with clear operational boundaries.
- Clients receive structured outputs and structured error payloads with stable contracts.
- Stage 8 remains intentionally narrow, enabling safe expansion in future stages without rework of duplicated logic.
