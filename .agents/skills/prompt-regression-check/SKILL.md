---
name: prompt-regression-check
description: Compare workflow behavior before and after prompt changes using deterministic eval metrics and objective pass/fail evidence.
---

# prompt-regression-check

## When to use
Use when prompt text changes may affect grounded workflow outputs and you need an objective before/after check.

## Expected inputs
- prompt change summary (what changed and where)
- target workflow(s): `ask`, `memo`, `extract_kpis`, `extract_risks`, `timeline`
- dataset path for comparison runs
- run labels (for example `before` and `after`) and output file names

## Expected outputs
- paired commands for before/after eval runs
- comparison summary using objective metrics
- explicit regression flags (if any)
- concrete next actions tied to failed metrics/cases

## Rules
- Use the same dataset for both runs.
- Save both outputs explicitly in `evals/results/` for traceable comparison.
- Use `--fail-on-fail` for regression checks.
- Evaluate only objective signals from runner outputs:
  - `pass_fail`
  - `schema_adherence`
  - `abstention_correctness`
  - `citation_presence`
  - `citation_accuracy`
  - `notes`
- Prioritize regressions in this order:
  1. schema adherence
  2. abstention correctness
  3. citation behavior (presence and accuracy)
- Avoid subjective wording (style, tone, fluency) unless directly tied to metric failures.

## Command pattern
- Before change:
  - `python -m evals.runner --dataset <dataset> --output-json evals/results/<label>_before.json --output-md evals/results/<label>_before.md --fail-on-fail`
- After change:
  - `python -m evals.runner --dataset <dataset> --output-json evals/results/<label>_after.json --output-md evals/results/<label>_after.md --fail-on-fail`

## Comparison checklist
- Summary deltas: passed vs failed case counts.
- Case-level regressions: previously pass -> now fail.
- Metric deltas for failed or changed cases.
- New or changed `notes` entries indicating concrete grounding problems.

## Output template
1. `Before command`
2. `After command`
3. `Regression summary`
4. `Cases to inspect`
5. `Recommended follow-up`
