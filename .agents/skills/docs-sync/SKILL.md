---
name: docs-sync
description: Keep README, architecture notes, and ADRs aligned with code changes using practical, stage-accurate updates.
---

# docs-sync

## When to use
Use when code changes affect commands, APIs, tool behavior, architecture boundaries, or stage-level design decisions.

## Expected inputs
- summary of code changes
- files changed
- stage context and scope boundaries
- whether behavior/contract changes are user-facing or internal

## Expected outputs
- docs update plan by file (`README.md`, `docs/architecture.md`, `docs/decisions/*.md`)
- exact sections to add, update, or leave unchanged
- consistency checklist to prevent mismatched docs

## Rules
- Update only docs that are actually affected by the code change.
- Keep documentation stage-accurate and practical.
- Do not document unimplemented or speculative features.
- Keep `README.md` focused on run/test/use guidance.
- Keep `docs/architecture.md` limited to additions for the current stage.
- Add/update ADRs only when a meaningful design decision changed.
- Ensure commands in docs are runnable and paths are correct.

## Repo mapping guide
- command/env/tooling changes -> `README.md`
- structural/runtime/component changes for current stage -> `docs/architecture.md`
- rationale/tradeoff/decision changes -> `docs/decisions/<next>-<topic>.md`

## Output template
1. `Docs to update`
2. `Planned section changes`
3. `Consistency checks`
4. `Out-of-scope docs left unchanged`
