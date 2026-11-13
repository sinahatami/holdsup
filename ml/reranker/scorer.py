"""The exported reranker, scored as the API serves it, and timed.

The scoring code is the API's own (`holdsup.ml.reranker`: onnxruntime and tokenizers, no
torch), so the latency in the report is measured on the code path P4.4 serves. An export
folder holds `model.onnx`, `tokenizer.json` and `reranker.json` (how to feed it, and what it
was trained on).
"""

import json
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from holdsup.ml.reranker import (
    META_FILE,
    ONNX_FILE,
    TOKENIZER_FILE,
    ExportMeta,
    OnnxReranker,
    Session,
    pair_tokenizer,
)

__all__ = [
    "META_FILE",
    "ONNX_FILE",
    "TOKENIZER_FILE",
    "ExportMeta",
    "Latency",
    "OnnxReranker",
    "Session",
    "measure",
    "pair_tokenizer",
    "write_meta",
]


class Latency(BaseModel):
    threads: int
    claims: int
    candidates_per_claim: float
    p50_ms: float
    p95_ms: float
    mean_ms: float


def measure(
    reranker: OnnxReranker, work: Sequence[tuple[str, Sequence[str]]], threads: int, warmup: int = 5
) -> Latency:
    """Wall time to score each claim's candidates, after a few warm-up calls."""
    for query, docs in work[:warmup]:
        reranker.logits(query, docs)
    times: list[float] = []
    for query, docs in work:
        start = time.perf_counter()
        reranker.logits(query, docs)
        times.append((time.perf_counter() - start) * 1000)
    ordered = sorted(times)
    return Latency(
        threads=threads,
        claims=len(times),
        candidates_per_claim=sum(len(d) for _, d in work) / len(work),
        p50_ms=round(float(np.percentile(ordered, 50)), 2),
        p95_ms=round(float(np.percentile(ordered, 95)), 2),
        mean_ms=round(sum(times) / len(times), 2),
    )


def write_meta(folder: Path, meta: ExportMeta) -> None:
    (folder / META_FILE).write_text(json.dumps(meta.model_dump(), indent=2) + "\n")
