"""Grouped k-fold: every claim of a group lands in the same fold, folds balanced by size."""

import random
from collections import Counter
from collections.abc import Sequence


def assign_folds(groups: Sequence[str], k: int, seed: int) -> dict[str, int]:
    """Each distinct group to a fold in 0..k-1. Biggest groups first, each into the fold with
    the fewest claims so far; a seeded shuffle orders groups of equal size, so a seed always
    gives the same split."""
    if k < 2:
        raise ValueError("k-fold needs at least 2 folds")
    counts = Counter(groups)
    if len(counts) < k:
        raise ValueError(f"{len(counts)} groups cannot fill {k} folds")
    order = sorted(counts)
    random.Random(seed).shuffle(order)  # noqa: S311 - a reproducible split, not security
    order.sort(key=lambda g: -counts[g])  # stable: the shuffle orders ties
    sizes = [0] * k
    out: dict[str, int] = {}
    for g in order:
        fold = min(range(k), key=lambda f: (sizes[f], f))
        out[g] = fold
        sizes[fold] += counts[g]
    return out
