"""The benchmark file: one JSON object per line, a text and the claims a person labelled in it.

`eval/smoke_claims.jsonl` and (P4.1) `eval/claims.jsonl` share this shape; see eval/README.md.
A typo in a label would quietly score as a model failure, so the file is validated strictly:
unknown keys, bad periods, unknown labels, duplicate ids and indicators the catalog does not
have are all errors, reported together.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from holdsup.catalog.schema import Catalog
from holdsup.pipeline.claim import LATEST, PERIOD_RE
from holdsup.verdict import Label

Split = Literal["dev", "test"]
# What a run reads: the dev split (and texts that name no split, such as the smoke file), the
# held-out test split, or both. Tuning uses dev only.
Selection = Literal["dev", "test", "all"]


class LabelledClaim(BaseModel):
    """One claim in a text, as a person read it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    quote: str
    indicator: str | None  # a catalog id; None when the catalog has nothing for it
    geo: str | None
    window: tuple[str, str]  # [start, end]; periods as in ClaimSpec, or "latest"
    expected: Label
    justification: str

    @field_validator("window")
    @classmethod
    def _periods(cls, window: tuple[str, str]) -> tuple[str, str]:
        for period in window:
            if period != LATEST and not PERIOD_RE.match(period):
                raise ValueError(f"{period!r} is not a period (2015, 2024-03, 2025-Q1) or 'latest'")
        return window


class BenchmarkText(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    text: str
    source_url: str | None = None
    added: str | None = None
    why: str | None = None  # a regression: what once went wrong
    split: Split | None = None
    claims: tuple[LabelledClaim, ...]


class BenchmarkError(Exception):
    """The benchmark file is not usable; the message lists every problem."""


def load_benchmark(path: Path) -> list[BenchmarkText]:
    """Read and validate `path`. Raises `BenchmarkError` listing every problem found."""
    texts: list[BenchmarkText] = []
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            texts.append(BenchmarkText.model_validate_json(line))
        except ValidationError as exc:
            for error in exc.errors():
                where = ".".join(str(p) for p in error["loc"])
                problems.append(f"{path.name}:{number}: {where}: {error['msg']}")
    seen: set[str] = set()
    for item in texts:
        if item.id in seen:
            problems.append(f"{path.name}: duplicate id {item.id!r}")
        seen.add(item.id)
        if not item.claims:
            problems.append(f"{path.name}: {item.id} has no labelled claims")
    if problems:
        raise BenchmarkError("\n".join(problems))
    return texts


def check_indicators(texts: Sequence[BenchmarkText], catalog: Catalog) -> None:
    """Every labelled indicator must be in the catalog. Raises `BenchmarkError`."""
    known = {s.id for s in catalog.indicators}
    problems = [
        f"{t.id}: indicator {c.indicator!r} is not in the catalog"
        for t in texts
        for c in t.claims
        if c.indicator is not None and c.indicator not in known
    ]
    if problems:
        raise BenchmarkError("\n".join(problems))


def select(texts: Sequence[BenchmarkText], selection: Selection) -> list[BenchmarkText]:
    """The texts of one split. A text with no split counts as dev."""
    if selection == "all":
        return list(texts)
    return [t for t in texts if (t.split or "dev") == selection]
