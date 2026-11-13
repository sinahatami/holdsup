"""Check eval/claims.jsonl (P4.1): schema, catalog ids, label mix and splits, with the runner's own loader.

Run like record_series.py, from the repo root:
    cd apps/api && uv run python -m scripts.check_benchmark ../../eval/claims.jsonl
Offline; it never fetches anything. Exit 1 on any problem the loader reports.
"""

import sys
from collections import Counter
from pathlib import Path

from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from scripts.evaluation.benchmark import BenchmarkError, check_indicators, load_benchmark

TARGET = {  # share of labelled claims, from the P4.1 brief (partly_supported is carved out of the first two)
    "supported": 0.38,
    "not_supported": 0.27,
    "supported_framing_matters": 0.20,
    "cant_check": 0.10,
    "partly_supported": 0.05,
}


def main(path: Path) -> int:
    try:
        texts = load_benchmark(path)
        check_indicators(texts, load_catalog(REPO_ROOT / "packages" / "catalog"))
    except BenchmarkError as exc:
        print(exc)
        return 1
    claims = [(t, c) for t in texts for c in t.claims]
    n = len(claims)
    print(f"{len(texts)} texts, {n} labelled claims")
    by_label = Counter(str(c.expected) for _, c in claims)
    for label, share in TARGET.items():
        print(
            f"  {label:27} {by_label.get(label, 0):4}  ({by_label.get(label, 0) / n:5.1%}, target {share:.0%})"
        )
    print("  splits:", dict(Counter(t.split or "dev" for t in texts)))
    test = Counter(str(c.expected) for t, c in claims if t.split == "test")
    if test:
        print("  test split by label:", dict(test))
    no_indicator = sum(c.indicator is None for _, c in claims)
    print(f"  claims with no catalog indicator: {no_indicator}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "eval/claims.jsonl")))
