# Stage 0 Architecture

## Scope

Stage 0 provides a minimal local development baseline. It includes:
- a backend API service
- a frontend web app
- a local Postgres instance

No authentication, upload flows, workers, or MCP integration are included at this stage.

## Components

### Backend (`backend/`)
- Framework: FastAPI
- Current endpoint: `GET /health`
- Purpose in Stage 0: verify API bootstrapping and test setup

### Frontend (`frontend/`)
- Framework: Next.js with TypeScript
- Current page: minimal landing page at `/`
- Purpose in Stage 0: verify frontend bootstrapping and local run/build flow

### Infrastructure (`infra/`)
- Service: Postgres (`postgres:16-alpine`) in Docker Compose
- Purpose in Stage 0: provide a local database container baseline

## Interactions in Stage 0

- Frontend does not call backend yet.
- Backend does not use Postgres yet.
- Postgres runs independently for local environment readiness.

## Repository boundaries

- Application code lives in `backend/`, `frontend/`, and `infra/`.
- Agent workflow assets live under `.agents/` and are intentionally separate from application code.
