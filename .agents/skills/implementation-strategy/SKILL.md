---
name: implementation-strategy
description: Plan incremental code changes with explicit scope, affected files, validation commands, and practical risk notes.
---

# implementation-strategy

## When to use
Use this skill when:
- the user asks for an implementation plan, strategy, or step breakdown
- the task touches multiple files or layers
- scope boundaries and validation must be explicit before coding

## When not to use
Do not use this skill for:
- trivial single-file edits where implementation is obvious
- broad product brainstorming not tied to concrete repository changes

## Expected inputs
- current stage and goal
- in-scope and out-of-scope items
- constraints (safety, grounded behavior, API/schema stability, determinism)
- known target areas (backend, frontend, evals, mcp_server, docs)
- required handoff items

## Expected outputs
- implementation steps (ordered, incremental, smallest viable slices)
- affected files (create/update list)
- validation commands (targeted checks first, then broader checks if needed)
- rollback or risk notes when useful

## Planning rules for this repository
- Lock scope to the current request; do not add future-stage features.
- Prefer minimal changes that preserve existing contracts.
- Reuse existing workflows/services; avoid duplicated business logic.
- Keep layer boundaries clear:
  - backend (`backend/`) for API/business logic
  - frontend (`frontend/`) for UI
  - evals (`evals/`) for datasets/runner/metrics
  - MCP (`mcp_server/`) for tool surface that reuses backend behavior
- Include test impact for each planned change.
- Include docs impact when commands, contracts, or architecture notes change.
- Avoid speculative refactors or new infrastructure unless explicitly required.

## Output template
Use this structure in responses:

1. `Implementation steps`
2. `Affected files`
3. `Validation commands`
4. `Risk or rollback notes` (only when relevant)
