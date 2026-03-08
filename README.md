# Research Copilot

Minimal FastAPI backend slice for the investment research copilot.

## Run locally

```bash
uvicorn app.main:app --reload
```

The service will be available at `http://127.0.0.1:8000`.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## API docs

FastAPI serves interactive docs by default:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run tests

```bash
pytest -q
```

## Configuration

Settings are loaded from environment variables with prefix `RESEARCH_COPILOT_`.

Examples:

- `RESEARCH_COPILOT_APP_NAME`
- `RESEARCH_COPILOT_ENVIRONMENT`
- `RESEARCH_COPILOT_DEBUG`
- `RESEARCH_COPILOT_LOG_LEVEL`
- `RESEARCH_COPILOT_LOG_JSON`

## Architecture readiness

The current foundation keeps transport, config, schemas, and logging separate so the next slices can be introduced without cross-coupling:

- ingestion
- retrieval
- generation
- verification
- evals
