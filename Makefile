# One command surface for humans and agents. See CLAUDE.md.
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load .env (development keys only) into every recipe, if present.
-include .env
export

# Embedding model cache, shared by tests, `make catalog`, and the API in dev.
FASTEMBED_CACHE_PATH ?= $(CURDIR)/.cache/fastembed
export FASTEMBED_CACHE_PATH

API_DIR := apps/api
WEB_DIR := apps/web

.PHONY: help setup dev dev-api dev-web lint lint-py lint-web test test-py test-web format db-migrate docker-api smoke-providers list-models pivot-test embed-model catalog catalog-check

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Python (uv) and JS (pnpm) deps, install lefthook hooks
	uv sync --all-packages --locked
	pnpm install --frozen-lockfile
	pnpm exec lefthook install

dev: ## Run the API (localhost:8000) and web (localhost:3000) together
	@$(MAKE) -j2 --no-print-directory dev-api dev-web

dev-api:
	cd $(API_DIR) && uv run uvicorn holdsup.main:app --reload --port 8000

dev-web:
	pnpm --filter @holdsup/web dev

lint: lint-py lint-web ## ruff, mypy --strict, eslint, prettier --check, tsc --noEmit

lint-py:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy $(API_DIR)

lint-web:
	pnpm --filter @holdsup/web lint
	pnpm exec prettier --check .
	pnpm --filter @holdsup/web typecheck

test: test-py test-web ## pytest with coverage, vitest

test-py:
	cd $(API_DIR) && uv run pytest --cov=holdsup --cov-report=term-missing --cov-report=xml --cov-fail-under=85

test-web:
	pnpm --filter @holdsup/web test --coverage

format: ## Auto-format Python and web code
	uv run ruff format .
	uv run ruff check --fix .
	pnpm exec prettier --write .

db-migrate: ## alembic upgrade head (uses DATABASE_URL)
	cd $(API_DIR) && uv run alembic upgrade head

docker-api: ## Build and run the API image on localhost:7860
	docker build -f $(API_DIR)/Dockerfile -t holdsup-api:dev .
	docker run --rm -p 7860:7860 --env-file $(if $(wildcard .env),.env,/dev/null) holdsup-api:dev

smoke-providers: ## Check JSON-schema output and tool calls on every provider (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.smoke_providers $(ARGS)

list-models: ## List model ids each provider serves to your keys (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.list_models $(ARGS)

pivot-test: ## Phase 1 pivot test over eval/seed_claims.csv -> eval/reports/pivot_test.csv (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.pivot_test $(ARGS)

embed-model: ## Download the embedding model into .cache/fastembed (needed by tests and catalog)
	cd $(API_DIR) && uv run python -c "from holdsup.catalog.embed import FastEmbedder; FastEmbedder('$(FASTEMBED_CACHE_PATH)')"

catalog-check: ## Validate packages/catalog without touching the database
	cd $(API_DIR) && uv run python -m holdsup.catalog.load --check

catalog: ## Validate packages/catalog, embed it, and load it into Postgres (needs DATABASE_URL)
	cd $(API_DIR) && uv run python -m holdsup.catalog.load
