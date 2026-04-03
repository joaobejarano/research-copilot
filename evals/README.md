# Stage 7 Local Evals Foundation

This folder contains a local, inspectable eval foundation for grounded research workflows.

## Structure

- `evals/schemas.py`: explicit Pydantic schemas for eval cases and eval results
- `evals/datasets/stage7_seed_cases.json`: seed eval dataset
- `evals/runner.py`: deterministic local runner foundation
- `evals/results/`: output reports from local runs

## Supported workflow types

- `grounded_qa`
- `memo_generation`
- `kpi_extraction`
- `risk_extraction`
- `timeline_building`

## Case schema

Each eval case supports:

- `id`
- `workflow_type`
- `document_reference`
- `input`
- `expected_behavior`
- optional `expected_fields`
- optional `expected_status`

## Result schema

Each eval result includes:

- `case_id`
- `workflow_type`
- `pass_fail`
- `metrics`
- `notes`

## Run locally

```bash
python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json
```

Optional: fail the command when any case fails.

```bash
python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json --fail-on-fail
```
