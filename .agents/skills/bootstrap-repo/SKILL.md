---
name: bootstrap-repo
description: Create or review the initial repository structure for the current stage with a minimal and testable setup.
---

# bootstrap-repo

## When to use
Use when creating or reviewing the initial repository structure for the current stage.

## Inputs
- target stack
- required folders
- current stage scope

## Output
- proposed or created folder tree
- missing files
- setup checklist
- suggested commit message

## Rules
- Keep the structure minimal.
- Do not add infrastructure that is not yet needed.
- Separate agent tooling from application code.
- Do not anticipate future stages.