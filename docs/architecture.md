# Stage 7 Architecture Additions

This document describes only what Stage 7 adds.

## Scope Added in Stage 7

- local eval foundation for grounded research workflows
- deterministic eval runner behavior and report outputs
- explicit eval metrics for practical local iteration
- backend human feedback persistence and API endpoints
- minimal dashboard human review panel integration
- feedback export path into future eval candidate cases

Out of scope in Stage 7:

- active learning pipelines
- advanced human moderation workflows
- auth for review actions
- Stage 8+ quality systems

## Components Added in Stage 7

### Evals foundation (`evals/`)

- `evals/schemas.py`
  - explicit schemas for datasets, fixtures, run results, and summaries
- `evals/datasets/stage7_seed_cases.json`
  - practical benchmark dataset with positive and negative cases
- `evals/runner.py`
  - executes existing workflows via local ASGI requests
  - seeds fixture documents/chunks for deterministic execution
  - computes deterministic metrics per case
  - writes JSON and Markdown reports

### Evals metrics

Stage 7 metrics are explicit and deterministic:

- `schema_adherence`
- `abstention_correctness`
- `citation_presence`
- `citation_accuracy`

Additional explicit checks included in results:

- `expected_status_match`
- `expected_fields_adherence`

### Backend feedback capture

- DB model: `backend/app/db/models/feedback.py`
- routes: `backend/app/api/routes/feedback.py`
- endpoints:
  - `POST /feedback`
  - `GET /feedback`

Captured fields:

- `workflow_type`
- `document_id`
- optional `target_id`
- optional `target_reference`
- `feedback_value` (`positive`/`negative`)
- optional `reason` (required for negative)
- optional `reviewer_note`
- `created_at`

### Minimal review UX

- dashboard page includes a practical review panel:
  - thumbs up / thumbs down actions
  - reason required for negative feedback
  - optional reviewer note
  - recent feedback listing for selected document

### Feedback -> eval follow-up export

- `evals/feedback_export.py`
  - reads stored feedback from the local database
  - filters rows (negative by default)
  - transforms supported workflows into eval case candidate templates
  - flags unsupported workflow rows in `skipped`
  - writes JSON export for manual curation into future datasets

## Stage 7 Runtime Flow

### Eval run flow

1. Load dataset and validate schema/references.
2. Seed local fixtures into DB.
3. Execute each case against workflow endpoint.
4. Score deterministic metrics.
5. Produce pass/fail summary.
6. Write JSON/Markdown reports.

### Human review flow

1. Analyst reviews workflow output.
2. Analyst submits positive/negative feedback.
3. Backend validates payload (negative requires reason).
4. Feedback record is persisted and can be listed.
5. Feedback export script produces follow-up eval candidates for future runs.

## Stage 7 Test Coverage Added

- eval dataset loading and validation tests
- eval runner behavior tests
- report generation tests (JSON and Markdown)
- feedback creation tests
- negative feedback reason handling tests
- feedback listing/filtering tests
- feedback export transformation tests
