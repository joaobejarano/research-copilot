# Agent Development Workflow

This document explains how to use code agents and local skills in this repository.

## 1) Role of `AGENTS.md`

`AGENTS.md` is the repository-level operating contract for agents.

Use it as the default source for:
- scope control (only implement the requested task)
- architecture guardrails (no premature abstractions/infrastructure)
- testing expectations before handoff
- documentation update expectations
- final handoff format

If a task is unclear, follow `AGENTS.md` first and keep changes minimal.

## 2) Role of `.agents/skills/`

`.agents/skills/` contains reusable task playbooks (`SKILL.md` files).

Each skill should define:
- when to use it
- expected inputs
- expected outputs
- practical rules and templates

Skills guide execution quality, but they do not override task scope or `AGENTS.md`.

## 3) Incremental Agent Workflow (Recommended)

1. Confirm task scope and out-of-scope items.
2. Choose the minimum relevant skill(s).
3. Implement in small, verifiable slices.
4. Run targeted checks for changed areas.
5. Update docs if behavior, commands, or architecture notes changed.
6. Deliver clear handoff (files changed, run/test info, expected result, commit message).

## 4) Choosing the Right Skill

Use this quick mapping:

- `implementation-strategy`
  - planning incremental implementation steps before coding
- `run-local-checks`
  - choosing deterministic validation commands and pass/fail checks
- `eval-runner`
  - selecting and running `evals.runner` commands and inspecting reports
- `prompt-regression-check`
  - before/after eval comparisons for prompt changes using objective metrics
- `docs-sync`
  - deciding which docs to update (`README.md`, architecture doc, ADRs)
- `update-readme`
  - focused README updates for run/setup/workflow changes
- `pr-draft-summary`
  - preparing concise PR/handoff summaries with tests and limitations
- `bootstrap-repo`
  - repository/stage bootstrap structure checks

## 5) Practical Rules

- Prefer one small change-set per task.
- Do not document or claim unimplemented features.
- Keep backend, frontend, evals, and MCP concerns separated unless task scope requires integration.
- Reuse existing workflows and contracts; avoid duplicating business logic.
