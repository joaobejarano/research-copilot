# Research Copilot

Research Copilot is in Stage 9.

Stage 9 polishes the development workflow for code agents and repository-maintenance assets.

## Stage 9: Development Workflow Polish

### How `AGENTS.md` is used

`AGENTS.md` is the repository-level operating contract for code agents. It defines:

- scope control (implement only the requested task)
- architecture guardrails (avoid premature abstractions/infrastructure)
- testing expectations before handoff
- documentation update expectations
- required handoff format

Agents should treat `AGENTS.md` as the default process source for repository work.

### What skills exist

Reusable skills live in `.agents/skills/`:

- `bootstrap-repo`
- `run-local-checks`
- `update-readme`
- `implementation-strategy`
- `eval-runner`
- `prompt-regression-check`
- `docs-sync`
- `pr-draft-summary`

### How to use code agents incrementally

Recommended flow for agent-driven changes:

1. Confirm scope and out-of-scope constraints.
2. Pick the minimum relevant skill(s).
3. Implement in small, testable slices.
4. Run targeted checks for changed areas.
5. Update docs if commands/contracts/architecture notes changed.
6. Handoff with files changed, run/test info, expected result, and commit message.

### Agent workflow guide

Use this developer guide for practical agent workflow details:

- `docs/agent-development-workflow.md`

### How to run repository-maintenance checks

Agent workflow asset checks:

```bash
.venv/bin/pytest -q tests/maintenance
```

Additional common checks:

```bash
.venv/bin/pytest -q mcp_server/tests
.venv/bin/pytest -q evals/tests
.venv/bin/pytest -q backend/tests
cd frontend && npm run typecheck
```
