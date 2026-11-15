"""GET /v1/eval: the benchmark's results, read from the reports committed in the repository."""

import asyncio

from fastapi import APIRouter

from holdsup.config import get_settings
from holdsup.router import load_router_config
from holdsup.service.benchmark import Benchmark, read_benchmark

router = APIRouter(tags=["evaluation"])


@router.get("/eval", response_model=Benchmark)
async def benchmark() -> Benchmark:
    """The head-to-head against a plain chatbot, every evaluation run, and the trained models'
    reports. Nothing is recomputed: it is what the committed reports say."""
    settings = get_settings()
    labels = {p.name: p.label for p in load_router_config().providers}
    # Reading a few files is blocking I/O, so it runs off the event loop.
    return await asyncio.to_thread(read_benchmark, settings.reports_dir, settings.ml_dir, labels)
