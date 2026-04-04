# Research Copilot

Research Copilot is in Stage 7.

Stage 7 adds a practical local evaluation foundation plus lightweight human review capture.

## Stage 7: Evals and Human Review

### How Stage 7 evals work

Stage 7 evals are local, explicit, and dataset-driven:

- eval cases are defined in JSON (`evals/datasets/stage7_seed_cases.json`)
- document fixtures are seeded into a local DB for deterministic execution
- the eval runner executes existing backend workflows through API endpoints
- each case produces explicit metric scores and pass/fail outcome
- JSON and Markdown reports are written for inspection and comparison

Supported workflow types:

- `ask`
- `memo`
- `extract_kpis`
- `extract_risks`
- `timeline`

### How to run the eval runner

```bash
python -m evals.runner --dataset evals/datasets/stage7_seed_cases.json --fail-on-fail
```

By default reports are written to `evals/results/`:

- `stage7_eval_report_<timestamp>.json`
- `stage7_eval_report_<timestamp>.md`

### Metrics currently implemented

Stage 7 starts with deterministic metrics:

- `schema_adherence`
- `abstention_correctness`
- `citation_presence`
- `citation_accuracy`

Additional explicit checks included in results:

- `expected_status_match`
- `expected_fields_adherence`

## Human Review (Lightweight)

Stage 7 adds backend feedback capture and a minimal analyst dashboard panel.

### How human review works

- Analysts review existing workflow outputs (currently practical path centered on grounded Q&A output in dashboard flow).
- Feedback is stored as structured records with:
  - `workflow_type`
  - `document_id`
  - optional target linkage (`target_id` or `target_reference`)
  - `feedback_value` (`positive` or `negative`)
  - optional `reason` (required for negative)
  - optional `reviewer_note`
  - `created_at`
- Recent feedback can be listed and filtered.

### Feedback endpoints

- `POST /feedback`
- `GET /feedback`

### How to submit feedback (curl)

Positive feedback:

```bash
curl -X POST "http://127.0.0.1:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "ask",
    "document_id": 1,
    "target_reference": "ask:answered:What happened to revenue in Q4?",
    "feedback_value": "positive",
    "reviewer_note": "Clear and grounded answer."
  }'
```

Negative feedback (reason required):

```bash
curl -X POST "http://127.0.0.1:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "ask",
    "document_id": 1,
    "target_reference": "ask:answered:What happened to revenue in Q4?",
    "feedback_value": "negative",
    "reason": "Answer missed key risk context.",
    "reviewer_note": "Need stronger citation grounding."
  }'
```

List feedback:

```bash
curl "http://127.0.0.1:8000/feedback?document_id=1&feedback_value=negative"
```

## Feedback as Future Eval Input

Stage 7 includes a lightweight export path to turn stored feedback into follow-up eval candidate cases.

Generate candidates (negative feedback by default):

```bash
python -m evals.feedback_export \
  --database-url "${DATABASE_URL}" \
  --feedback-value negative \
  --limit 200 \
  --output evals/results/feedback_followup_candidates.json
```

The generated file includes:

- `summary` (scanned/generated/skipped)
- `candidates` with `eval_case_candidate` templates
- `skipped` rows (for workflows outside current Stage 7 eval runner scope)

## Required Environment Variables

Core backend/runtime:

- `DATABASE_URL` (or `POSTGRES_*` values)
- `STORAGE_DIR`

Retrieval/workflow settings used by eval and normal runs:

- `RETRIEVAL_TOP_K`
- `RETRIEVAL_MIN_SIMILARITY`
- `MAX_WORKFLOW_CITATIONS`
- `MAX_WORKFLOW_ITEMS`

If using hosted LLM provider in normal runs:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY` (when provider is OpenAI)

Frontend dashboard (for review panel):

- `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`

## Run Backend and Frontend

Backend:

```bash
cd backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## How to run tests

Run all backend tests:

```bash
pytest -q backend/tests
```

Run eval and feedback-focused tests:

```bash
pytest -q evals/tests backend/tests/test_feedback.py
```
