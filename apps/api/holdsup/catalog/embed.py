"""Local embeddings with fastembed (D007). Vectors are L2-normalized, so dot = cosine."""

import math
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIM = 384


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else list(vector)


class FastEmbedder:
    dim = DIM

    def __init__(self, cache_dir: str | None = None, local_only: bool = False) -> None:
        from fastembed import TextEmbedding  # heavy import; only when embeddings are needed

        self._model = TextEmbedding(MODEL_NAME, cache_dir=cache_dir, local_files_only=local_only)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [normalize(v.tolist()) for v in self._model.embed(list(texts))]


@lru_cache
def default_embedder(cache_dir: str | None = None) -> FastEmbedder:
    return FastEmbedder(cache_dir)
