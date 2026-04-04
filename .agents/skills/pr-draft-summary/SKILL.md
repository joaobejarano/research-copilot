---
name: pr-draft-summary
description: Draft a practical PR summary with scope, key files, testing evidence, and known limitations.
---

# pr-draft-summary

## When to use
Use when preparing a PR description or handoff note after implementation work is complete.

## Expected inputs
- task scope and explicit out-of-scope items
- main files changed
- tests/checks executed and their outcomes
- known limitations, risks, or deferred follow-ups

## Expected outputs
- concise scope summary
- major files changed with one-line purpose each
- testing performed with commands and results
- known limitations/follow-ups listed clearly

## Rules
- Report only work done in the current change set.
- Separate implemented behavior from follow-up ideas.
- Include concrete test commands and pass/fail outcomes.
- Call out unrun checks explicitly with reason.
- Keep wording factual and avoid marketing language.
- Keep summary aligned with AGENTS.md handoff requirements.

## Output template
1. `Scope`
2. `Major files changed`
3. `Testing performed`
4. `Known limitations or follow-ups`
5. `Suggested commit message`
