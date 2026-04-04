SHELL := /bin/bash

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= $(ROOT_DIR)/.venv/bin/python
UVICORN ?= $(ROOT_DIR)/.venv/bin/uvicorn
PYTEST ?= $(ROOT_DIR)/.venv/bin/pytest

COMPOSE_FILE ?= infra/docker-compose.yml
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
BACKEND_URL ?= http://$(BACKEND_HOST):$(BACKEND_PORT)
EVAL_DATASET ?= evals/datasets/stage7_seed_cases.json

.PHONY: help infra-up infra-down infra-logs backend-run backend-test frontend-run mcp-run \
	evals-run project-run health-check api-smoke mcp-test evals-test maintenance-test \
	tests validate-workflows clean

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "; printf "\nAvailable targets:\n"} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

infra-up: ## Start local infrastructure with Docker Compose
	docker compose -f $(COMPOSE_FILE) up -d

infra-down: ## Stop local infrastructure
	docker compose -f $(COMPOSE_FILE) down

infra-logs: ## Tail infrastructure logs
	docker compose -f $(COMPOSE_FILE) logs -f

backend-run: ## Run FastAPI backend locally (reload enabled)
	cd backend && $(UVICORN) app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

backend-test: ## Run backend tests
	$(PYTEST) -q backend/tests

frontend-run: ## Run Next.js frontend locally
	cd frontend && npm run dev

mcp-run: ## Run MCP server locally
	$(PYTHON) -m mcp_server

mcp-test: ## Run MCP server tests
	$(PYTEST) -q mcp_server/tests

evals-run: ## Run eval runner with fail-on-fail
	$(PYTHON) -m evals.runner --dataset $(EVAL_DATASET) --fail-on-fail

evals-test: ## Run eval harness tests
	$(PYTEST) -q evals/tests

maintenance-test: ## Run repository-maintenance checks
	$(PYTEST) -q tests/maintenance

tests: ## Run all local test suites used in this repository
	$(MAKE) backend-test
	$(MAKE) mcp-test
	$(MAKE) evals-test
	$(MAKE) maintenance-test

project-run: ## Run backend, frontend, and MCP server together (Ctrl+C stops all)
	@echo "Starting backend, frontend, and MCP server..."
	@trap 'kill 0' INT TERM EXIT; \
		( cd backend && $(UVICORN) app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT) ) & \
		( cd frontend && npm run dev ) & \
		( $(PYTHON) -m mcp_server ) & \
		wait

health-check: ## Check backend health endpoint
	curl -fsS $(BACKEND_URL)/health | $(PYTHON) -m json.tool

api-smoke: ## Run minimal API smoke checks (/health and /documents)
	curl -fsS $(BACKEND_URL)/health > /dev/null
	curl -fsS $(BACKEND_URL)/documents > /dev/null
	@echo "API smoke checks passed: /health and /documents"

validate-workflows: ## Validate important local workflows (health + smoke + maintenance checks)
	$(MAKE) health-check
	$(MAKE) api-smoke
	$(MAKE) maintenance-test

clean: ## Remove common local caches and generated eval reports
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache backend/.pytest_cache evals/.pytest_cache mcp_server/.pytest_cache
	rm -f evals/results/stage7_eval_report_*.json evals/results/stage7_eval_report_*.md
