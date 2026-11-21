# HoldsUp API

The FastAPI backend: it extracts claims, matches them to catalog indicators, fetches the series, recomputes each claim in code, and returns a verdict with a receipt. The [root README](../../README.md) explains the method; this page is a map for working on the code.

## Run it

From the repository root (the commands are the same for everyone):

```bash
make dev-api      # uvicorn with reload on localhost:8000 (make dev also starts the site)
make db-migrate   # Alembic upgrade head
make catalog      # validate packages/catalog and load it into Postgres
```

Settings come from environment variables, read by `holdsup/config.py`. `.env.example` in the root lists every one with a comment. New checks need at least one live provider key (`GROQ_API_KEY` is tried first).

## Endpoints

Everything is under `/v1`. Errors are [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem details. The interactive schema is at `/docs` while the API runs.

| Method and path                                 | What it does                                                         |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `POST /checks`                                  | Start a check on pasted text or an article link (202 with an id)     |
| `GET /checks/{id}/stream`                       | Server-Sent Events: `step_started`, `step_done`, then `result`/`error` |
| `GET /checks/{id}`                              | A stored check                                                       |
| `GET /checks/{id}/notebook`                     | The receipt as a Jupyter notebook that recomputes the result         |
| `POST /checks/{id}/claims/{index}/recheck`      | Check one claim again                                                |
| `POST /checks/{id}/reports`                     | Report a wrong match                                                 |
| `GET /gallery`                                  | Featured checks, for the home and recent-checks pages                |
| `GET /catalog`, `GET /indicators`               | The indicator catalog, and a search over it                          |
| `GET /tolerances`, `GET /health`                | The verdict tolerances in use, and a liveness probe                  |

## Layout (`holdsup/`)

| Folder          | What is there                                                                          |
| --------------- | -------------------------------------------------------------------------------------- |
| `routes/`       | One module per resource, mounted on the `/v1` router; `deps.py` provides dependencies  |
| `pipeline/`     | The steps: extract, match, plan, then running the plan (`run.py`)                      |
| `router/`       | Every model call goes through here: `providers.yaml`, budgets, circuit breaker         |
| `ops/`          | Pure arithmetic (changes, trends, extremes, aggregates). The model never computes a number you see    |
| `checks/`       | Framing checks: cherry-picked windows, distortions, change points                      |
| `verdict/`      | Rules that turn computed results into a label, with `tolerances.yaml`                  |
| `receipt/`      | The notebook that replays a check with the standard library only                       |
| `adapters/`     | Eurostat, World Bank and Our World in Data clients                                     |
| `catalog/`      | Loading, indexing and vector search over the catalog                                   |
| `page/`         | Reading an article link safely (address guard, fetch, text extraction)                 |
| `service/`      | The runner, wiring, check store (memory or SQL) and rate limits                        |
| `db/`           | SQLAlchemy models, session and Alembic migrations                                      |
| `ml/`           | Inference for the reranker; training lives in the root `ml/` folder                    |

`scripts/` holds one-off and scheduled jobs run through `make`: the claim watch, gallery seeding, fixture recording, provider smoke tests and the evaluation runner.

## Tests

`make test-py` runs pytest with coverage. No test touches the network: adapters run against recorded responses in `tests/fixtures/`, and router tests use fake providers. The store and catalog tests also need a Postgres with pgvector in `TEST_DATABASE_URL` and skip without it; CI starts one.

## Deploy

The image is built by `make api-bundle` and the `Dockerfile` here. Every merge to `main` that touches the API checks the image (`.github/workflows/image.yml`) and then deploys it to Cloud Run (`cd.yml`). [DEPLOY.md](../../DEPLOY.md) has the one-time setup.
