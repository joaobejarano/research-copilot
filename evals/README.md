# Stage 7 Local Evals Runner

This folder contains a local, inspectable eval runner for grounded research workflows.

## Structure

- `evals/schemas.py`: explicit Pydantic schemas for dataset fixtures and results
- `evals/datasets/stage7_seed_cases.json`: seed eval dataset with document fixtures and cases
- `evals/runner.py`: deterministic local runner that executes existing backend workflows
- `evals/results/`: output reports from local runs

## Supported workflow types

- `ask`
- `memo`
- `extract_kpis`
- `extract_risks`
- `timeline`

## Case schema

Each eval case supports:

- `id`
- `workflow_type`
- `document_reference`
- `input`
- `expected_behavior`
- optional `expected_fields`
- optional `expected_status`
- optional `expected_abstention`

Dataset also includes `document_fixtures` used to seed local documents/chunks for execution.

## Result schema

Each eval result includes:

- `case_id`
- `workflow_type`
- `pass_fail`
- `endpoint_path`
- `http_status_code`
- `observed_status`
- `metrics`
- `notes`

## Initial deterministic metrics

- `schema_adherence`
- `abstention_correctness`
- `citation_presence`
- `citation_accuracy`

## Run locally

```bash
python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json --fail-on-fail
```

By default it writes:

- JSON report: `evals/results/stage7_eval_report_<timestamp>.json`
- Markdown report: `evals/results/stage7_eval_report_<timestamp>.md`
