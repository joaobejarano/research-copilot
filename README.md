# Research Copilot

Research Copilot is currently in Stage 0, with a minimal local setup:
- a FastAPI backend with a `/health` endpoint
- a Next.js frontend with a simple landing page
- a local Postgres service via Docker Compose

## Repository structure

```text
backend/   FastAPI application and backend tests
frontend/  Next.js (TypeScript) application
infra/     Local infrastructure (docker-compose)
docs/      Project documentation and architecture decisions
.agents/   Agent workflows and skills (kept separate from app code)
```

## Run the backend

1. Install dependencies:
```bash
cd backend
python -m pip install -r requirements-dev.txt
```

2. Start the API:
```bash
uvicorn app.main:app --reload
```

3. Open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Start local infrastructure

Start Postgres:
```bash
docker compose -f infra/docker-compose.yml up -d
```

Stop Postgres:
```bash
docker compose -f infra/docker-compose.yml down
```

## Run tests

Backend tests:
```bash
cd backend
pytest -q
```

Frontend build check:
```bash
cd frontend
npm run build
```
