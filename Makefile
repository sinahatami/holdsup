# One command surface for humans and agents.
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
ML_DIR := ml

.PHONY: help setup dev dev-api dev-web lint lint-py lint-web test test-py test-web test-ui e2e lighthouse analyze types fonts seed-gallery watch format db-migrate docker-api api-bundle api-image deploy-api deploy-setup smoke-providers list-models pivot-test eval-smoke eval-baseline eval eval-chatbot ml-setup test-ml reranker-paraphrase reranker-train confidence-train record-extractions record-series embed-model catalog catalog-check missing-report reports

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Python (uv) and JS (pnpm) deps, install lefthook hooks
	uv sync --all-packages --locked
	cd $(ML_DIR) && uv sync --locked
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
	cd $(ML_DIR) && uv run --locked mypy .

lint-web:
	pnpm --filter @holdsup/web lint
	pnpm exec prettier --check .
	pnpm --filter @holdsup/web typecheck

test: test-py test-ml test-web ## pytest with coverage, vitest

test-py:
	cd $(API_DIR) && uv run pytest --cov=holdsup --cov-report=term-missing --cov-report=xml --cov-fail-under=85
	@echo "ops/ must stay at 100% line coverage (Testing standards):"
	cd $(API_DIR) && uv run coverage report --include='holdsup/ops/*' --fail-under=100 --skip-covered

test-ml: ## ml/ tests (dataset, leakage guard, metrics, report; no torch, no network)
	cd $(ML_DIR) && uv run --locked pytest -q

test-web:
	pnpm --filter @holdsup/web test --coverage

test-ui: ## Web tests in a browser window: pick, rerun and inspect each test (reruns on save)
	pnpm --filter @holdsup/web test:ui

e2e: ## Playwright against a mocked API (incl. axe accessibility checks)
	pnpm --filter @holdsup/web e2e

lighthouse: ## Production build against the mock API, then the Lighthouse CI budget (home and a result page)
	pnpm --filter @holdsup/web lighthouse

analyze: ## Bundle analyzer (Turbopack): an interactive treemap of every route's JS
	pnpm --filter @holdsup/web analyze

types: ## Regenerate apps/web/src/lib/api/schema.ts from FastAPI's OpenAPI schema
	cd $(API_DIR) && uv run python -m scripts.export_openapi $(CURDIR)/.cache/openapi.json
	pnpm --filter @holdsup/web exec openapi-typescript $(CURDIR)/.cache/openapi.json -o src/lib/api/schema.ts
	pnpm exec prettier --write $(WEB_DIR)/src/lib/api/schema.ts

fonts: ## Cut Newsreader to the weights and sizes the site sets -> apps/web/src/app/fonts (downloads the pinned sources once)
	uv run scripts/trim_fonts.py

seed-gallery: ## Run eval/gallery_claims.txt and feature the results (needs keys, DATABASE_URL, catalog; not CI)
	cd $(API_DIR) && uv run python -m scripts.seed_gallery $(ARGS)

watch: ## Claim watch (S1): compare stored checks with the sources, publish updates for revised figures; no model or key (needs DATABASE_URL; ARGS="--dry-run" previews, "--backfill" plans pre-S1 checks with the plan model)
	cd $(API_DIR) && uv run python -m scripts.watch $(ARGS)

format: ## Auto-format Python and web code
	uv run ruff format .
	uv run ruff check --fix .
	pnpm exec prettier --write .

db-migrate: ## alembic upgrade head (uses DATABASE_URL)
	cd $(API_DIR) && uv run alembic upgrade head

docker-api: ## Build and run the API image on localhost:7860 (as development)
	docker build -f $(API_DIR)/Dockerfile -t holdsup-api:dev .
	docker run --rm -p 7860:7860 --env-file $(if $(wildcard .env),.env,/dev/null) \
		-e APP_ENV=development holdsup-api:dev

# Everything the API image needs, from committed files only (git archive: never .env or
# local edits), with the Dockerfile at the root and the commit stamped in for receipts.
# One folder per commit, .cache/api-<commit>; an existing one is left as it is.
API_BUNDLE_FILES := LICENSE pyproject.toml uv.lock apps/api/pyproject.toml apps/api/alembic.ini \
	apps/api/holdsup apps/api/scripts/fetch_reranker.py packages/catalog eval/VERSION \
	eval/reports ml/reranker/reports/report.json ml/confidence/reports/report.json
api-bundle: ## Write the API image's build folder for HEAD into .cache/api-<commit>
	@git diff --quiet HEAD -- $(API_BUNDLE_FILES) $(API_DIR)/Dockerfile || \
		echo "warning: uncommitted changes are not in the bundle (it is built from HEAD)"
	@commit=$$(git rev-parse --short HEAD); dir=.cache/api-$$commit; \
	if [ -e $$dir ]; then echo "$$dir already exists (the bundle for $$commit)"; exit 0; fi; \
	mkdir -p .cache && tmp=$$(mktemp -d .cache/api-partial.XXXXXX) && \
	git archive HEAD $(API_BUNDLE_FILES) | tar -x -C $$tmp && \
	git show HEAD:$(API_DIR)/Dockerfile \
		| sed 's/^ARG APP_COMMIT=""$$/ARG APP_COMMIT="'"$$commit"'"/' > $$tmp/Dockerfile && \
	grep -q "^ARG APP_COMMIT=\"$$commit\"" $$tmp/Dockerfile && \
	mv $$tmp $$dir && echo "API bundle for $$commit in $$dir"

# Google Cloud Run (DEPLOY.md). GCP_PROJECT is your Google Cloud project id; GCP_REGION is the
# region nearest your Neon database: us-east4 (N. Virginia) for Neon's AWS us-east-1, where the
# site's database is (Vercel's functions run there too, apps/web/vercel.json). Images go to the
# Artifact Registry repository `holdsup` in that region.
GCP_REGION ?= us-east4
API_SERVICE := holdsup-api
API_IMAGE = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/holdsup/api
api-image: api-bundle ## Build HEAD's API image and push it to Artifact Registry (GCP_PROJECT=…)
	@test -n "$(GCP_PROJECT)" || { echo "Set GCP_PROJECT: make $@ GCP_PROJECT=<project id>"; exit 2; }
	@commit=$$(git rev-parse --short HEAD); \
	docker build --platform linux/amd64 -t $(API_IMAGE):$$commit .cache/api-$$commit && \
	docker push $(API_IMAGE):$$commit && echo "Pushed $(API_IMAGE):$$commit"

deploy-api: api-image ## Push HEAD's API image and switch the Cloud Run service to it (GCP_PROJECT=…)
	gcloud run deploy $(API_SERVICE) --project $(GCP_PROJECT) --region $(GCP_REGION) \
		--image $(API_IMAGE):$$(git rev-parse --short HEAD)

deploy-setup: ## One-time: let GitHub Actions (cd.yml) deploy the API without a stored key (GCP_PROJECT=…)
	@test -n "$(GCP_PROJECT)" || { echo "Set GCP_PROJECT: make $@ GCP_PROJECT=<project id>"; exit 2; }
	./scripts/setup-deploy.sh $(GCP_PROJECT) $(GCP_REGION)

smoke-providers: ## Check JSON-schema output and tool calls on every provider (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.smoke_providers $(ARGS)

list-models: ## List model ids each provider serves to your keys (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.list_models $(ARGS)

pivot-test: ## Phase 1 pivot test over eval/seed_claims.csv -> eval/reports/pivot_test.csv (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.pivot_test $(ARGS)

# Local eval runs replay saved model replies (scripts/evaluation/replay.py): a request already asked
# is answered from .cache, so only a changed prompt, model or series spends free-tier quota. A
# whole run prunes the replies it did not use, so the smoke set and the dev split each get a
# folder. Opt out with ARGS="--record DIR" (asks everything afresh), or ARGS="--replay DIR" for
# another folder; the held-out run (--final) asks afresh unless it is given one of those.
SMOKE_REPLIES ?= .cache/eval-replies
DEV_REPLIES ?= .cache/eval-replies-dev
replay_by_default = $(if $(or $(findstring --record,$(ARGS)),$(findstring --replay,$(ARGS)),$(findstring --final,$(ARGS))),,--replay $(1))

eval-smoke: ## Smoke evaluation (eval/smoke_claims.jsonl) -> eval/reports/smoke.{json,md}; fails on a verdict-accuracy drop over 5 points vs eval/baseline.json; replays saved model replies from .cache/eval-replies (ARGS="--record DIR" asks afresh; needs keys; not CI's unit tests)
	cd $(API_DIR) && uv run python -m scripts.evaluation --claims eval/smoke_claims.jsonl --name smoke --gate $(call replay_by_default,$(SMOKE_REPLIES)) $(ARGS)

eval-baseline: ## Accept the current smoke run as eval/baseline.json (after reading the report; needs keys)
	cd $(API_DIR) && uv run python -m scripts.evaluation --claims eval/smoke_claims.jsonl --name smoke --update-baseline $(ARGS)

eval: ## Full dev-split evaluation of eval/claims.jsonl -> eval/reports/dev.{json,md}; manual, rate-limited providers; replays saved model replies from .cache/eval-replies-dev (ARGS="--provider NAME" for one provider; ARGS=--resume continues a stopped run; ARGS="--record DIR" asks afresh)
	cd $(API_DIR) && uv run python -m scripts.evaluation $(call replay_by_default,$(DEV_REPLIES)) $(ARGS)

eval-chatbot: ## The head-to-head baseline: one plain chatbot model answers the same claims -> eval/reports/dev.chatbot.<provider>.{json,md} (P4.6; manual; the baseline step's first model unless ARGS="--provider NAME"; --resume; the test split needs --final, P4.7)
	cd $(API_DIR) && uv run python -m scripts.evaluation.chatbot_cli $(ARGS)

ml-setup: ## ml/ environment with the training libraries (torch CPU wheels, sentence-transformers, onnx)
	cd $(ML_DIR) && uv sync --locked --group train

reranker-paraphrase: ## Reword the dev-split claims for reranker training -> ml/reranker/data/paraphrases.jsonl (offline: Gemini, else Groq; resumes)
	cd $(ML_DIR) && uv run --locked python -m reranker.paraphrase

reranker-train: ## Cross-validate on the dev split, train, export ONNX -> ml/reranker/artifacts, reports/, MODEL_CARD.md (after ml-setup; over an hour on CPU; ARGS="--quick DIR" for a few-minute check)
	cd $(ML_DIR) && uv run --locked --group train python -m reranker.experiment $(ARGS)

confidence-train: ## Cross-validate the confidence model on dev evaluation reports (default eval/reports/dev.json; ARGS="--report A --report B" for several runs) -> ml/confidence/reports/, and apps/api/holdsup/ml/confidence_model.json only if it beats the base rate
	cd $(ML_DIR) && uv run --locked python -m confidence.experiment $(ARGS)

record-extractions: ## Record live extraction responses for the P2.1 tests (needs keys; not CI)
	cd $(API_DIR) && uv run python -m scripts.record_extractions $(ARGS)

record-series: ## Record adapter output for the pipeline regression tests (network; not CI)
	cd $(API_DIR) && uv run python -m scripts.record_series $(ARGS)

reranker-fetch: ## Download the pinned reranker (apps/api/holdsup/ml/reranker_pin.json) from the Hugging Face Hub into ml/reranker/artifacts/onnx, sha256-checked; never overwrites a different local file (network)
	cd $(API_DIR) && uv run python -m scripts.fetch_reranker holdsup/ml/reranker_pin.json ../../ml/reranker/artifacts/onnx

embed-model: ## Download the embedding model into .cache/fastembed (needed by tests and catalog)
	cd $(API_DIR) && uv run python -c "from holdsup.catalog.embed import FastEmbedder; FastEmbedder('$(FASTEMBED_CACHE_PATH)')"

catalog-check: ## Validate packages/catalog without touching the database
	cd $(API_DIR) && uv run python -m holdsup.catalog.load --check

missing-report: ## List the topics most often asked about that came back "can't check" (needs DATABASE_URL; read-only)
	cd $(API_DIR) && uv run python -m scripts.missing_report $(ARGS)

reports: ## List the newest reports of a wrong match, with a link to each check (needs DATABASE_URL; read-only)
	cd $(API_DIR) && uv run python -m scripts.list_reports $(ARGS)

catalog: ## Validate packages/catalog, embed it, and load it into Postgres (needs DATABASE_URL)
	cd $(API_DIR) && uv run python -m holdsup.catalog.load
