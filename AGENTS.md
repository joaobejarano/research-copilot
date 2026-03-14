# AGENTS.md

## Project objective
Research Copilot is built incrementally, one integrable step at a time.

## Working mode
- Only implement the scope explicitly requested in the current step.
- Do not anticipate future roadmap steps.
- Prefer minimal, testable, production-oriented changes.
- Stop after completing the requested deliverable.

## Repo rules
- Keep agent workflow files separate from application code.
- Do not add MCP code before the dedicated MCP stage.
- Do not add background workers before they are explicitly required.
- Keep backend and frontend changes isolated unless explicitly requested.
- Do not introduce business features outside the current stage.

## Backend conventions
- Use FastAPI.
- Keep routes thin.
- Prefer explicit and simple structure over abstractions.
- Avoid service layers until real business workflows appear.

## Frontend conventions
- Use Next.js with TypeScript.
- Keep the first UI minimal.
- Do not add complex state management in bootstrap stages.

## Delivery rules
Every task must end with:
- files changed
- how to run
- how to test
- expected result
- suggested commit message