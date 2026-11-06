"""Shared catalog test helpers."""

import hashlib
import math
from collections.abc import Sequence
from pathlib import Path

FIXTURE_CATALOG = Path(__file__).resolve().parents[1] / "fixtures" / "catalog"


class HashEmbedder:
    """Deterministic bag-of-words embedder: no model, no network. Shared words → similar."""

    dim = 384

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * self.dim
            for word in text.lower().replace(".", " ").replace(";", " ").split():
                v[int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.dim] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out
