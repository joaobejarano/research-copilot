# Stage 4 Architecture Additions

This document describes only what Stage 4 adds on top of Stage 3 backend capabilities.

## Scope Added in Stage 4

- minimal analyst dashboard page in frontend (`/documents`)
- frontend API client integration with existing backend endpoints
- list and selection flow for documents
- selected document detail panel
- explicit processing action from the dashboard
- chunk inspection UI
- grounded Q&A UI with citation rendering
- local loading, empty, and error states per section

Still out of scope in Stage 4:

- memo generation UI
- multi-document dashboard workflows
- advanced filtering/pagination
- authentication

## Frontend Structure Added

### API client layer (`frontend/src/lib`)

- `api/client.ts`
  - shared JSON request wrapper
  - normalizes API error handling
- `api/models/documents.ts`
  - typed request/response contracts for:
    - list documents
    - document detail
    - process document
    - document chunks
    - grounded ask
- `api/documents.ts`
  - explicit endpoint functions with no complex abstraction
- `config/env.ts`
  - frontend runtime config for `NEXT_PUBLIC_API_BASE_URL`

### Dashboard page (`frontend/src/app/documents/page.tsx`)

Single page with local React state for:

- document list loading/error/empty
- selected document detail loading/error
- processing action status and failure feedback
- chunks loading/error/empty
- grounded Q&A submit/loading/error/result

The page intentionally avoids global state libraries and keeps fetch logic explicit in the route component.

## Stage 4 Runtime Flow

1. Frontend loads `/documents`.
2. UI requests `GET /documents` and renders the list.
3. Selecting a row triggers:
  - `GET /documents/{document_id}`
  - `GET /documents/{document_id}/chunks`
4. For non-ready documents, user can trigger:
  - `POST /documents/{document_id}/process`
  - then refresh detail and chunks
5. For grounded Q&A:
  - user submits question
  - frontend calls `POST /documents/{document_id}/ask`
  - UI renders `question`, `answer`, `status`, and `citations`

## UX Behavior in Stage 4

- sections are intentionally simple: detail, grounded Q&A, and chunks
- long chunk and citation text uses scrollable containers for readability
- each section has explicit loading and error states with retry controls
- empty states are present when no documents/chunks/results are available
