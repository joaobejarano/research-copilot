# AGENTS.md

## Goal
Build an investment research copilot for company documents and earnings materials.

## Product constraints
- Backend must be Python + FastAPI.
- Prefer Postgres + pgvector for retrieval.
- Every user-facing answer must be grounded in retrieved evidence.
- If evidence is insufficient, prefer abstaining over guessing.
- Use structured outputs whenever possible.

## Engineering rules
- Before making large changes, propose the file tree and implementation plan.
- Prefer small, reviewable diffs.
- Do not add new production dependencies without justification.
- Keep code, comments, and commit messages in English.
- Every retrieval or prompt change must include or update eval coverage.
- Add or update tests for every non-trivial behavior change.
- Keep prompt logic isolated from transport and persistence code.

## Repository expectations
- Run `pytest -q` before considering a task done.
- Run `ruff check .` after Python changes.
- Run `mypy app` on touched backend modules when possible.
- Document important architectural decisions in `docs/`.

## Architecture guidance
- Keep ingestion, retrieval, generation, verification, and evaluation separated.
- Avoid framework-heavy abstractions unless they clearly reduce complexity.
- Prefer explicit service modules over hidden magic.
- Keep the first version simple and production-credible.

## LLM workflow guidance
- Generator step must only use retrieved evidence.
- Verifier step must check grounding, citation quality, and missing-evidence cases.
- If the answer is not well supported, return uncertainty instead of fabrication.

## Evals guidance
- Maintain a small but representative eval set.
- Track at least: faithfulness, citation accuracy, and numerical consistency.
- When changing retrieval, inspect whether the failure is chunking, metadata filtering, or ranking.
- When changing prompts, compare before/after behavior on the same eval set.

## MCP usage
- Always use the OpenAI developer documentation MCP server if you need to work with the OpenAI API, ChatGPT Apps SDK, Codex, AGENTS.md, skills, or MCP-related questions without me having to explicitly ask.
- Use the local `research_tools` MCP server for project-specific helper tools when relevant.

## Initial delivery order
1. Minimal FastAPI app
2. `/health` endpoint
3. Config loading from environment
4. Basic tests
5. Local MCP server
6. Eval harness scaffold
7. Retrieval foundation
8. First grounded generation flow