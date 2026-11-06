# One command surface for humans and agents. See CLAUDE.md.
SHELL := /bin/bash
.DEFAULT_GOAL := help

API_DIR := apps/api
WEB_DIR := apps/web

.PHONY: help setup dev dev-api dev-web lint lint-py lint-web test test-py test-web format

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
