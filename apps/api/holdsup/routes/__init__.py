"""HTTP routes. `v1` mounts every route module under /v1; `main.create_app` includes it.

A new route module adds its `router` here. Handlers get their collaborators from `deps`.
"""

from fastapi import APIRouter

from holdsup.routes import checks, indicators, meta

v1 = APIRouter(prefix="/v1")
v1.include_router(meta.router)
v1.include_router(indicators.router)
v1.include_router(checks.router)
