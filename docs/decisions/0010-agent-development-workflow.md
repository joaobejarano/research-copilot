# ADR 0010: Stage 9 Agent Development Workflow

- Status: Accepted
- Date: 2026-04-04

## Context

By Stage 9, the repository includes multiple delivery surfaces (`backend/`, `frontend/`, `evals/`, `mcp_server/`) plus growing agent support assets (`AGENTS.md`, local skills, workflow docs). Without explicit workflow guidance, agent-driven changes can drift in scope, documentation, and validation rigor.

Stage 9 focuses on process polish, not product expansion.

## Decisions

1. Keep `AGENTS.md` concise and operational
- `AGENTS.md` defines core guardrails (scope, architecture boundaries, testing, docs, handoff).
- Avoid turning it into a long handbook.
- Rationale: concise rules are easier to apply consistently across tasks.
- Rationale: shorter guidance reduces interpretation overhead during implementation.

2. Split skills into narrow reusable units
- Keep each skill focused on one repeatable workflow (planning, eval execution, prompt regression checks, docs sync, PR summary).
- Compose skills as needed per task instead of creating monolithic playbooks.
- Rationale: narrow skills improve reuse and reduce coupling between unrelated processes.
- Rationale: focused skills are easier to maintain as repository workflows evolve.

3. Treat agent workflow as engineering process, not product functionality
- Agent workflow assets stay in repository-maintenance scope (`AGENTS.md`, `.agents/skills/`, `docs/agent-development-workflow.md`).
- Do not expose agent workflow polish as end-user product capability.
- Rationale: this keeps process changes separate from customer-facing behavior.
- Rationale: enables workflow iteration without product contract impact.

4. Keep repository checks lightweight
- Add small, practical checks for required workflow assets (required files exist).
- Avoid building heavy validation frameworks for Stage 9.
- Rationale: lightweight checks catch common drift with low maintenance cost.
- Rationale: aligns with incremental delivery and fast local iteration.

## Consequences

- Agent tasks are more consistent in scope control, validation, and documentation updates.
- Skill usage becomes clearer and more reusable across maintenance tasks.
- Repository process quality improves without adding product complexity.
- Validation coverage exists for critical workflow assets while remaining low-overhead.
