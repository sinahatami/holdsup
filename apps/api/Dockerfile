# HoldsUp API image (Hugging Face Spaces Docker, port 7860).
# Build from the repository root, because the uv workspace lock lives there:
#   docker build -f apps/api/Dockerfile -t holdsup-api .

FROM ghcr.io/astral-sh/uv:0.11.23 AS uv

FROM python:3.13-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src

# Dependencies first, so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package holdsup --no-install-workspace

COPY apps/api apps/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package holdsup --no-editable

# Bake the embedding model into the image so the API never downloads it at request time.
FROM build AS model
ENV FASTEMBED_CACHE_PATH=/opt/fastembed
RUN /opt/venv/bin/python -c "from holdsup.catalog.embed import FastEmbedder; FastEmbedder('/opt/fastembed')"

# The fine-tuned indicator reranker (D030): the files named in the pin, from the Hugging Face
# Hub at the pinned commit, each sha256-checked (any mismatch fails the build). The stage holds
# only the pin and the standard-library script, so it downloads again only when the pin changes.
FROM python:3.13-slim AS reranker
COPY apps/api/holdsup/ml/reranker_pin.json apps/api/scripts/fetch_reranker.py /fetch/
RUN python -I /fetch/fetch_reranker.py /fetch/reranker_pin.json /opt/reranker

FROM python:3.13-slim AS runtime
# The commit shown on receipts: --build-arg APP_COMMIT=$(git rev-parse --short HEAD)
# (on Hugging Face Spaces, set it as a Space variable).
ARG APP_COMMIT=""
# Hugging Face Spaces runs containers as uid 1000.
RUN useradd --create-home --uid 1000 app
COPY --from=build /opt/venv /opt/venv
COPY --from=model --chown=app:app /opt/fastembed /opt/fastembed
# Read-only: the API checks these files against the pin again when it loads them.
COPY --from=reranker /opt/reranker /opt/reranker
COPY --chown=app:app apps/api/alembic.ini /app/alembic.ini
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed \
    RERANKER_DIR=/opt/reranker \
    PORT=7860 \
    APP_COMMIT=${APP_COMMIT}
WORKDIR /app
USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/v1/health', timeout=4)"]
CMD ["sh", "-c", "exec uvicorn holdsup.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
