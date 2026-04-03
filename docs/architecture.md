# Stage 6 Architecture Additions

This document describes only what Stage 6 adds to the backend.

## Scope Added in Stage 6

- reliability schemas for verification, confidence, gating, and agent traces
- reliability service with explicit threshold-based gate decisions
- grounded citation verification for Q&A answers
- constrained research agent orchestration over existing internal tools
- document-scoped reliability endpoints and responses

Out of scope in Stage 6:

- multi-agent orchestration
- human review UI/workflow execution
- frontend agent experience
- MCP/tooling beyond existing internal workflows

## Backend Components Added

### Reliability schemas (`backend/app/reliability/schemas.py`)

Stage 6 introduces strict models for:

- verification checks and outcomes (`VerificationCheckResult`, `VerificationOutcome`)
- confidence signals and result (`ConfidenceSignal`, `ConfidenceResult`)
- gate thresholds and decisions (`GateThresholds`, `GateDecision`)
- agent execution trace (`AgentToolCallTrace`, `AgentExecutionTrace`)
- consolidated assessment (`ReliabilityAssessment`)

### Reliability service (`backend/app/reliability/service.py`)

`ReliabilityService` provides explicit, deterministic mechanics:

- summarize verification checks into `passed`, `inconclusive`, or `failed`
- compute confidence score/band from weighted signals and verification score
- decide gate result (`pass`, `review`, `block`) using configured thresholds
- build and finalize agent traces with per-tool call status

### Grounded evaluator (`backend/app/reliability/grounded.py`)

`GroundedAskReliabilityEvaluator` evaluates grounded Q&A output by checking:

- citation exists in stored chunks
- citation belongs to the requested document
- citation excerpt is present in referenced chunk text
- answer numeric claims are supported by cited chunks

It returns:

- verification result
- confidence result
- gate decision
- issues list

### Constrained agent (`backend/app/workflows/agent.py`)

`ConstrainedResearchAgent` is document-scoped and deterministic:

- accepts one free-form instruction
- selects only from allowed tools (`ask`, `memo`, `extract_kpis`, `extract_risks`, `build_timeline`)
- executes selected tools in deterministic order
- records full execution trace
- applies confidence gating before returning outputs

## Stage 6 API Additions

### `POST /documents/{document_id}/verify/ask`

- runs grounded Q&A plus reliability evaluation
- returns verification, confidence, gate decision, and issues

### `POST /documents/{document_id}/agent`

- runs constrained agent orchestration for one document
- returns:
  - selected tools
  - execution trace
  - outputs (withheld unless gate passes)
  - confidence
  - gate decision
  - explicit status (`passed`, `needs_review`, `blocked`)

## Stage 6 Runtime Behavior

### Verification flow

1. Run grounded Q&A for one `document_id`.
2. Verify citations and grounded excerpts.
3. Compute confidence signals.
4. Apply explicit gate decision.
5. Return verification/confidence/gate details.

### Agent flow

1. Select tools deterministically from instruction.
2. Execute selected tools within one document scope.
3. Record per-tool execution trace.
4. Build verification and confidence results.
5. Apply gate decision:
- `passed`: return outputs
- `needs_review`: withhold outputs and return reasons
- `blocked`: withhold outputs and return reasons

## Test Coverage Added in Stage 6

- reliability schema and service behavior tests
- grounded evaluator tests for citation checks and numeric claim support
- endpoint tests for `/verify/ask`
- constrained agent endpoint tests for:
  - passed outcome
  - needs_review outcome
  - blocked outcome
  - deterministic trace behavior
