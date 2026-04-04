---
name: eval-runner
description: Select and run the correct local eval command, then summarize report outputs and key inspection points.
---

# eval-runner

## When to use
Use when a task requires running local evals and interpreting results for existing workflow behavior.

## Expected inputs
- target scope (all evals, specific workflow, or specific case IDs)
- dataset path (default: `evals/datasets/stage7_seed_cases.json`)
- output preference (default output paths vs explicit files)
- whether failures should fail the command (`--fail-on-fail`)

## Expected outputs
- exact eval command chosen
- expected console output and exit-code behavior
- report paths to inspect (JSON and optionally Markdown)
- concise checklist of what to inspect in report results

## Rules
- Prefer the repository runner: `python -m evals.runner`.
- Default to deterministic local dataset unless user specifies another dataset.
- Use `--fail-on-fail` when validating regressions or gating handoff.
- Keep report paths explicit when comparing multiple runs:
  - `--output-json <path>`
  - `--output-md <path>`
- Focus inspection on objective fields:
  - `summary.total_cases`, `summary.passed_cases`, `summary.failed_cases`
  - per-case `pass_fail`, `http_status_code`, `observed_status`
  - metrics: `schema_adherence`, `abstention_correctness`, `citation_presence`, `citation_accuracy`
  - `notes` for concrete failure reasons
- Do not infer quality from stylistic wording; use metric and notes evidence only.

## Command patterns
- Baseline run:
  - `python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json`
- Strict regression run:
  - `python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json --fail-on-fail`
- Comparable saved outputs:
  - `python -m evals.runner --dataset <dataset> --output-json evals/results/<name>.json --output-md evals/results/<name>.md --fail-on-fail`

## Output template
1. `Command`
2. `Expected output`
3. `Reports to inspect`
4. `Inspection checklist`
