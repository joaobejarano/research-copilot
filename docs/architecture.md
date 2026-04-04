# Stage 9 Architecture Additions

This document describes only what Stage 9 adds.

## Scope Added in Stage 9

- repository-level agent workflow contract refinement in `AGENTS.md`
- reusable skill library expansion in `.agents/skills/`
- lightweight developer-facing workflow guide for agents
- lightweight repository-maintenance checks for required agent assets

Out of scope in Stage 9:

- product feature changes
- new business workflows
- heavy validation frameworks or CI platform expansion

## Components Added in Stage 9

### Agent operating contract

- `AGENTS.md`
  - keeps scope control explicit
  - defines incremental implementation expectations
  - defines testing-before-handoff and docs update requirements
  - keeps architecture guardrails practical and concise

### Reusable agent skills

- `.agents/skills/implementation-strategy/SKILL.md`
- `.agents/skills/eval-runner/SKILL.md`
- `.agents/skills/prompt-regression-check/SKILL.md`
- `.agents/skills/docs-sync/SKILL.md`
- `.agents/skills/pr-draft-summary/SKILL.md`

These complement existing skills and provide narrow reusable guidance for planning, eval validation, docs synchronization, and PR/handoff drafting.

### Agent workflow documentation

- `docs/agent-development-workflow.md`
  - explains role of `AGENTS.md`
  - explains role of `.agents/skills/`
  - defines incremental agent workflow for this repository
  - maps common tasks to specific skills

### Lightweight repository checks

- `tests/maintenance/test_agent_workflow_assets.py`
  - checks `AGENTS.md` exists
  - checks required skill files exist
  - checks required agent workflow docs exist

## Stage 9 Runtime/Process Flow

1. Agent reads `AGENTS.md` and task scope.
2. Agent selects a narrow skill from `.agents/skills/`.
3. Agent implements incremental changes and runs targeted checks.
4. Agent updates docs when contracts/commands/workflow guidance change.
5. Maintenance tests confirm required agent assets are present.

## Stage 9 Design Constraints Enforced

- Agent workflow is repository process infrastructure, not product runtime behavior.
- Skills are intentionally narrow and composable.
- Validation remains lightweight and practical.
- Documentation reflects only implemented repository behavior.
