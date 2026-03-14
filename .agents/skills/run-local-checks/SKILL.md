---
name: run-local-checks
description: Validate that the current stage runs locally using deterministic checks and clear pass or fail criteria.
---

# run-local-checks

## When to use
Use when validating that the current stage is runnable locally.

## Output
- commands to run
- expected outputs
- common failure points
- pass/fail checklist

## Rules
- Prefer deterministic checks.
- Separate backend, frontend, and infrastructure validation.
- Include the expected result for each command.