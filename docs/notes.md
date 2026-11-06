# HoldsUp — Working notes

## P1.1 Monorepo skeleton

Plan:
- Root: pnpm workspace (`apps/web`), uv workspace (`apps/api`), `Makefile`, `.env.example`, `.nvmrc` (26), `.python-version` (3.13), `engines` in both package.json files, Prettier.
- `apps/api`: FastAPI app factory, `GET /v1/health` → `{"status":"ok"}`, pydantic-settings config, pytest test.
- `apps/web`: create-next-app 16.4.5, React 19.3.1, Tailwind 4.3.5, shadcn/ui on Base UI (`base-nova` style, RTL on), home page from `src/lib/strings.ts`, Vitest + RTL placeholder test.
- Placeholders: `packages/catalog` (VERSION 0.1.0), `ml/`, `eval/` (VERSION 0.1.0).

Choices made (spec ambiguous or tools moved):
- TypeScript pinned to 5.9.3, not 7.0.x: the scaffold and eslint-config-next target 5.x; revisit when typescript-eslint supports 7.
- ESLint pinned to 9.39.5 (scaffold default; eslint-config-next 16.4 flat config).
- `shadcn init -b base` alone produced the Radix `new-york` style; `-b base -p nova` gives `base-nova` with `@base-ui/react`.
- shadcn's new `cn` package (by shadcn) replaces clsx + tailwind-merge.
- `typecheck` runs `next typegen` first, because `LayoutProps` is a generated global.
- `make lint` runs `prettier --check .` from the root; Markdown and `docs/` are excluded from Prettier.
- Starlette warns that `TestClient` with `httpx` is deprecated in favour of `httpx2`. Kept `httpx` (it is the spec's HTTP client); revisit in P1.2/Renovate.
- `make setup` does not install lefthook hooks yet; that is P1.2.
- `next dev` re-creates `apps/web/AGENTS.md`, so it is committed.
- No `/v1` route for the web yet; the home page is static text.

Result: `make setup && make dev` serves `GET /v1/health` → `{"status":"ok"}` and the home page renders "HoldsUp / Every number has a denominator."; `make lint` and `make test` green (2 pytest, 1 vitest).

## P1.2 Tooling

Plan: lefthook (pre-commit ruff/eslint/prettier on staged files, commit-msg commitlint, pre-push mypy + `make test`), commitlint with `@commitlint/config-conventional`, release-please (single version for the repo), Renovate (grouped weekly). `make setup` installs the hooks.

Config files:
- `lefthook.yml`: hooks above. Installed by `make setup` (`pnpm exec lefthook install`). Skip once with `LEFTHOOK=0 git commit ...` (avoid).
- `commitlint.config.mjs`: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:` ...).
- `release-please-config.json` + `.release-please-manifest.json`: one `simple` release for the whole repo at `.`, tags `vX.Y.Z`, writes `CHANGELOG.md`, and bumps the version in `package.json`, `apps/web/package.json`, and `apps/api/pyproject.toml`. Starts at 0.0.0; minor bumps for features before 1.0. The GitHub Action that runs it comes with CI (P1.3/P5.2).
- `renovate.json`: weekly (Monday before 6am UTC), pinned versions, 3-day minimum release age, groups: Python, web minor/patch, GitHub Actions; web majors separate; weekly lockfile maintenance. The human must install the Renovate GitHub App on the repo.

Choices:
- Tailwind pinned to 4.3.4, not 4.3.5: 4.3.5 was published today and pnpm 12's default `minimumReleaseAge` (1 day) rejects it. The lockfile was rebuilt without the exemptions pnpm had added.
- ESLint stays on 9.39.5 (pnpm marks it deprecated): eslint-plugin-react, -jsx-a11y and -import (via eslint-config-next 16.4.5) don't declare ESLint 10 support.
- `lefthook` is allowed to run its postinstall in `pnpm-workspace.yaml` (`allowBuilds`).

Result: `git commit -m "updated some stuff"` is rejected by commitlint (2 problems: subject-empty, type-empty); conventional messages pass. Lint and tests green.

## P1.3 CI

Plan: `.github/workflows/ci.yml` (quality job = `make lint`; unit-tests job = `make test` with pytest-cov XML + Vitest v8 coverage, uploaded as an artifact), `gitleaks.yml` (PRs, main, weekly), `codeql.yml` (python, javascript-typescript, actions; PRs, main, weekly). Actions pinned to current majors (checkout v7, setup-node v7, setup-uv v7, pnpm/action-setup v6, codeql-action v4, gitleaks-action v3, upload-artifact v7); Renovate keeps them current.

Choices:
- `make test` now enforces backend coverage ≥ 85% (`--cov-fail-under=85`) and runs Vitest with `--coverage` (new dev dep `@vitest/coverage-v8`, D013).
- gitleaks-action is free for personal accounts; an organisation would need a `GITLEAKS_LICENSE` secret.

Branch protection (human, GitHub → Settings → Branches → Add rule for `main`):
1. Require a pull request before merging (0 approvals is fine for a solo repo); allow squash merging only (Settings → General → Pull Requests) and use the PR title as the commit message.
2. Require status checks to pass, and require branches to be up to date. Required checks: `Quality (ruff, mypy, eslint, tsc, prettier)`, `Unit tests with coverage`, `gitleaks`, `CodeQL (python)`, `CodeQL (javascript-typescript)`, `CodeQL (actions)`. They appear in the picker after the first CI run.
3. Block force pushes and deletions; include administrators.
4. Settings → Code security: enable CodeQL alerts view, secret scanning, and push protection.

Status: workflows committed and the branch is pushed; P1.3 is NOT ticked. Its "Done when" (a PR runs all jobs green) needs a pull request, and `gh` is not installed here. Waiting for the human to open the PR and report the CI result.

## P1.4 Deploy skeletons

Plan: `apps/api/Dockerfile` (python:3.13-slim, uv, port 7860, uid 1000), `.dockerignore`, `apps/web/vercel.json`, `DATABASE_URL` → async SQLAlchemy engine (`holdsup/db/`), Alembic (async template) with migration `0001` enabling `vector`, keep-alive workflow, `make db-migrate`, `make docker-api`.

Choices:
- The Docker build context is the repo root (`docker build -f apps/api/Dockerfile .`), because `uv.lock` is a workspace lock at the root. Only the `holdsup` package and its non-dev deps go into the image (~300 MB).
- `alembic.ini` uses `script_location = holdsup.db:migrations` so migrations run both from the source tree and from the installed package in the image.
- `holdsup/db/url.py` converts Neon's `postgres://…?sslmode=require&channel_binding=require` to `postgresql+asyncpg://…?ssl=require` (asyncpg rejects `sslmode` and `channel_binding`).
- `DATABASE_URL` is a `SecretStr`; it never appears in reprs or logs.
- Migrations are tested offline (`--sql`), so tests stay hermetic. Checked once by hand against `pgvector/pgvector:pg17` in Docker: upgrade created `vector 0.8.7`, downgrade removed it.
- The Makefile now loads the root `.env` (if present) into every recipe.
- Keep-alive pings `$API_BASE_URL/v1/health` every 12 hours (Spaces sleeps after ~48 h idle) and skips quietly while the variable is unset.
- Fix from P1.3: ESLint ignored `apps/web/coverage/`, so `make lint` no longer fails after `make test`.

Deployment steps (human):

Neon (database)
1. Create a project (Postgres default version, region near the Space, e.g. AWS eu-central-1). Copy the pooled connection string.
2. Locally: put it in `.env` as `DATABASE_URL`, then `make db-migrate`. Expect `Running upgrade -> 0001`.

Hugging Face Spaces (API)
1. Create a Space: SDK **Docker**, blank template, free CPU hardware.
2. Space Settings → Variables and secrets: add secret `DATABASE_URL`, and variable `WEB_ORIGIN` = the Vercel URL (e.g. `https://holdsup.vercel.app`). Provider keys come later (P1.5).
3. Spaces build from a `Dockerfile` at the Space repo root, and this image needs the root `uv.lock`, so a subtree push of `apps/api` won't work. Instead, clone the Space repo locally and copy in `pyproject.toml`, `uv.lock`, `apps/api/`, and `apps/api/Dockerfile` as `Dockerfile` at its root, plus a `README.md` with Space front matter:
   ```
   ---
   title: HoldsUp API
   sdk: docker
   app_port: 7860
   ---
   ```
   Commit and push to the Space. (A GitHub Action that does this on release can come later.)
4. When the build finishes, open `https://<user>-<space>.hf.space/v1/health` → `{"status":"ok"}`.

Vercel (web)
1. New Project → import the GitHub repo → Root Directory `apps/web` (keep "Include files outside the root directory" on, for the pnpm workspace). Framework is detected as Next.js; `vercel.json` sets the install and build commands.
2. Environment variable `HOLDSUP_API_URL` = the Space URL (used from P2.7 on).
3. Production branch `main`.

GitHub
1. Settings → Secrets and variables → Actions → **Variables**: `API_BASE_URL` = the Space URL (no trailing slash). Run "Keep-alive" once via workflow_dispatch to check.

Local check: `make docker-api` then `curl localhost:7860/v1/health`.

Result: image builds and runs locally (health `{"status":"ok"}`, Docker health check `healthy`, runs as uid 1000, `alembic upgrade head --sql` works inside it). 12 pytest tests (93% coverage), lint green.

## P1.5 Model router

Plan: `holdsup/router/` = `providers.yaml` + `config.py` (Pydantic, validated), `client.py` (openai SDK, SDK retries off, HTTP errors → typed errors), `budgets.py` (per-minute in-memory window, per-day `provider_usage` table, 90% caps), `breaker.py` (3 consecutive failures → 60 s open, then half-open), `router.py` (filter → order → call → fail over), `errors.py` (`RouterError` for callers). Migration `0002` adds `provider_usage`.

How a call is routed (`Router.complete(step, messages, use=Use.LIVE|OFFLINE, schema=Model, tools=...)`):
1. Candidates = the step's preference list, filtered by `allowed_use` (offline providers never serve `live`), capabilities (schema → `json_object`/`json_schema`; tools → `tools`), and API key present.
2. Skip any provider that is cooling down (429), exhausted for the day, has an open breaker, or is at 90% of its per-minute or per-day limit.
3. Count the request (minute window + `provider_usage`) before calling; add tokens after success.
4. 429 → cool down for `Retry-After` (`retry-after-ms`, seconds, or HTTP date), or 60 s without one. A 429 whose message mentions a daily quota (`per day`, `RPD`, `TPD`, `free-models-per-day`, …) → exhausted until 00:00 UTC.
5. Timeout, 5xx, connection errors, other 4xx → breaker failure; next provider.
6. Invalid JSON or schema-invalid → one retry on the same provider with the validation error appended; then next provider.
7. Nothing left → `RouterError(step, attempts, retry_after_s)`, where `retry_after_s` is the soonest any candidate frees up (for the "at capacity, back in N minutes" message).

Choices:
- Each provider entry is a provider + model (Groq's limits are per model).
- Model ids in `providers.yaml` are best guesses until P1.6's smoke script confirms them; `gemini-2.5-flash` and the OpenRouter `:free` model especially. Mistral has no published daily request cap, so only `requests_per_minute: 60` is set.
- Gemini is protected twice: `allowed_use: offline` filtering, and a config validator that rejects any Gemini entry (by name or `googleapis.com` URL) marked `live`.
- Daily quotas are assumed to reset at 00:00 UTC for every provider; adjust per provider if the consoles say otherwise.
- `json_object` providers get the JSON Schema in a system message; `json_schema` providers get it as `response_format`.
- Router state (cool-downs, breakers, minute windows) is per process, in memory; only daily counts are durable.
- Logging uses stdlib `logging` for now; structlog arrives with request IDs in P2.6.
- `openai` 3.x uses `httpx2`; client tests use `httpx2.MockTransport` (D014).
- `SqlUsageStore` has an integration test that runs only with `TEST_DATABASE_URL` set. Run here against `pgvector/pgvector:pg17`: passed.

Result: 55 router tests (fault injection: 429 with and without Retry-After, daily-limit 429, 90% daily and minute budgets, timeout, 5xx, connection error, other 4xx, malformed JSON body, invalid JSON output, schema-invalid output, breaker open/half-open/close, exhaustion → `RouterError`, Gemini never selected for `live` including on the shipped `providers.yaml`). Backend coverage 95%.

## P1.6 Provider smoke script

Plan: `apps/api/scripts/smoke_providers.py`, run with `make smoke-providers` (loads `.env`). For each provider in `providers.yaml` it builds a one-provider router (so calls still go through the router) with `use=offline` (so Gemini is checked too) and makes two calls:
1. **json_schema**: "capital of Italy" with a `{country, capital}` Pydantic schema; `ok` only if it parses and the capital is Rome.
2. **tools**: a forced (`tool_choice="required"`) `search_catalog(query: string)` call; `ok` only if the call comes back with a string `query` argument. `n/a` if the provider is not configured with the `tools` capability.

Output format (one row per provider; exit code 1 if any provider *with a key* has a `FAIL`):

```
| provider           | model                   | use  | key | json_schema | tools | max_ms | note                          |
|--------------------|-------------------------|------|-----|-------------|-------|--------|-------------------------------|
| groq-llama-3.3-70b | llama-3.3-70b-versatile | live | yes | ok          | ok    | 640    |                               |
| mistral-small      | mistral-small-latest    | live | yes | ok          | FAIL  | 910    | tools: ['mistral-small:rejected'] |
| gemini-flash       | gemini-2.5-flash        | offline | no | -        | -     | -      | GEMINI_API_KEY not set        |
```

- `key`: whether the provider's env var is set. Rows without a key are skipped, not failed.
- `max_ms`: slowest of the two calls.
- `note`: why a check failed (router attempt outcomes such as `rate_limited`, `rejected`, `malformed`), an unexpected answer, or "needed a repair retry" when the JSON was only valid after the router's schema-repair retry (worth knowing per provider).

What to do with the result (human): fix model ids in `providers.yaml` for `rejected`/404 rows; drop `json_schema` or `tools` from a provider's `capabilities` if that check fails; paste the table into this file with the date.

Result: the script runs without keys (all rows "not set", exit 0); its logic is unit-tested with fake providers.

## P1.7 Eurostat adapter

Plan: `holdsup/adapters/base.py` (Observation, FetchedSeries, typed errors), `jsonstat.py` (pure JSON-stat 2.0 decoder), `eurostat.py` (`EurostatAdapter.fetch_series(dataset, filters)` over httpx with tenacity retries), `scripts/record_fixture.py` (fixture manifest + recorder), fixtures in `tests/fixtures/eurostat/`.

Choices:
- `fetch_series` returns `FetchedSeries` (observations + `raw_sha256`, URL, retrieval time, labels, `updated`) instead of a bare `list[Observation]`, so the receipt and `series_cache` (P1.8) get the hash and citation from the same call. `.observations` is the list the task names.
- The decoder emits one Observation per cell, including missing ones (`value=None`), in cube order; `include_missing=False` drops them. Missing-but-flagged cells keep their status (e.g. `c` confidential).
- Every non-geo/time dimension is kept on `Observation.dims` (freq, unit, sex, age, s_adj, …) so callers can check they got the series they asked for.
- Handles both JSON-stat forms: category `index` as array or object (positions authoritative, not key order), `value`/`status` dense or sparse; a string `status` applies to all cells. NaN/inf become missing.
- HTTP: 400/404 → `SourceNotFound` (with Eurostat's error label); 5xx, 429, transport errors → 3 attempts with exponential backoff, then `SourceUnavailable`; a cube with no values at all → `SourceNotFound`.
- Fixtures are stored byte-for-byte (Prettier ignores `apps/api/tests/fixtures/`) so hashes are stable. `make`-free re-record: `cd apps/api && uv run python -m scripts.record_fixture [name]`.
- Ordering is checked against ground truth from separate single-geo queries (where the flat index is just the time position), not by re-deriving the index in the test. `flat_index` also has a hypothesis bijection property test.
- Not handled yet: Eurostat's asynchronous responses for very large extractions (the catalog uses small, filtered queries).

Result: 38 adapter tests (decoder ordering incl. out-of-order object index, missing values, status flags, 15 malformed-input cases; three recorded datasets: monthly multi-geo with a no-data month, annual with b/d flags, annual GDP with a missing LI value and p/e flags; HTTP 404/400/5xx/429/transport retry paths). Backend coverage 97%.

## P1.8 World Bank and OWID adapters, series_cache

Plan: `adapters/http.py` (shared GET + tenacity retries, moved out of Eurostat), `worldbank.py`, `owid.py`, `cache.py` (`CachedFetcher` + in-memory and Postgres stores), migration `0003` (`series_cache`), fixtures recorded via `scripts/record_fixture.py`.

Choices:
- One adapter shape for all sources: `fetch_series(dataset, filters) -> FetchedSeries` (`SeriesAdapter` protocol). Filters per source: Eurostat = its dimension codes (`geo`, `unit`, …); World Bank = `country` (ISO2/ISO3, one or many), `date` ("2010:2025"); OWID = `country` (ISO3), `time` ("2015..2023"), `column` (only when a chart has several value columns).
- World Bank: the HTTP-200 error block (`[{"message": [...]}]`) → `SourceNotFound` with key, value and id; an unknown country (HTTP 200, `total: 0`, data `null`) → `SourceNotFound` "no values". Pages are followed (max 20) and `raw_sha256` hashes all page bodies in order. `Observation.geo` is the ISO2 id (matches Eurostat); ISO3 is in `dims["iso3"]`.
- OWID: 403 → `SourceNotRedistributable` (not retried; the caller should mark it can't-check, never cache it). 404 → `SourceNotFound`. `geo` is the ISO3 code, or the entity name when the row has no code (e.g. "US Henry Hub"). Unit, title and citation come from `<chart>.metadata.json`; only the CSV is hashed (metadata contains a changing `dateDownloaded`).
- **The OWID 403 fixture is hand-written** (`tests/fixtures/owid/error_403_not_redistributable.txt`): about 20 likely charts all returned 200 or 404 on 2026-11-06. The adapter keys only on the status code, so the body text doesn't matter. Replace it with a real recording if a 403 chart turns up.
- Cache key = (source, code, sha256 of canonical filters); filter order and list order don't matter. Entries younger than 24 hours are returned without calling the adapter; older ones are refetched and upserted. Rows and metadata are JSONB, so a cached `FetchedSeries` round-trips exactly.
- The cache stores successful fetches only; errors are not cached.

Result: 139 backend tests with Postgres (137 + 2 DB-backed, skipped without `TEST_DATABASE_URL`): World Bank normal/gaps/error block/empty/pagination/malformed, OWID CSV + metadata/no-ISO entities/403/404/multi-column/malformed, cache hit avoids the adapter, 24 h expiry, upsert on Postgres. Backend coverage 96%.

## P1.9 Catalog

Plan: `holdsup/catalog/` = `schema.py` (Pydantic `IndicatorSpec`, `load_catalog` reporting every problem at once), `embed.py` (fastembed `BAAI/bge-small-en-v1.5`, normalized 384-d vectors), `index.py` (pgvector `SqlIndex` + `InMemoryIndex`), `load.py` (`make catalog` / `make catalog-check`); `indicators` table with an HNSW cosine index (migration `0004`); `GET /v1/indicators?q=&limit=` (default 8, max 20).

Choices:
- Added a `filters` field to the entry schema (fixed adapter query dimensions such as Eurostat `sex`/`age`/`unit`); the spec's field list has no place for them and the pivot test needs to fetch the exact series. Documented in `packages/catalog/README.md`.
- The validator enforces the spec's "3–5 aliases"; also: id = file name, related ids exist, no duplicate aliases, no two entries for the same source series + filters.
- `make catalog` syncs the table to the YAML (deletes removed entries) and stamps `catalog_version` from `packages/catalog/VERSION`.
- Embedding model: tests never download it. `make embed-model` puts it in `.cache/fastembed` (gitignored; the Makefile exports `FASTEMBED_CACHE_PATH`), CI downloads it in a cached setup step before `make test`, and the Docker image bakes it in at `/opt/fastembed` (checked: embeds with `--network none`). Without the model, the real-model search tests skip.
- Embedding runs in a worker thread (`asyncio.to_thread`) so search doesn't block the event loop.
- No query prefix for bge queries: aliases and paraphrases already rank first on the test catalog.
- Tests use a 6-entry test catalog in `apps/api/tests/fixtures/catalog/` (not the real catalog). The real `packages/catalog` is empty until P1.10 and must always validate (tested).
- Image size is now ~750 MB (onnxruntime, numpy, model).

Result: `make catalog` loads all entries (0 in `packages/catalog` today; 6 from the test catalog via `python -m holdsup.catalog.load tests/fixtures/catalog`) on Postgres 17 + pgvector. Every alias (18) and 4 unseen paraphrases find their indicator in the top 3 with the real model (all rank 1). Live `GET /v1/indicators?q=jobless rate for young people` returns `youth_unemployment_rate` first (0.84). 183 tests + 3 DB tests green.
