"""Training rows for the confidence model: one per claim an evaluation run gave a verdict
(other than cant_check), with the signals the check recorded and whether the verdict was right.

The rows come from evaluation reports of the dev split (`make eval`), never the test split:
a report of another split is refused, and so is any claim the benchmark holds out, so a report
written by hand or by mistake cannot leak held-out answers into training. Several reports (runs
on other days or providers) can be read together; a claim in two runs is two rows in one group,
so cross-validation never trains on one run of a claim and tests on another.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from holdsup.ml.confidence import Confidence, Signals, vector
from reranker.benchmark import Claim
from reranker.leakage import LeakageError

CANT_CHECK = "cant_check"


class _Outcome(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    text_id: str
    index: int
    status: str
    verdict: str | None = None
    verdict_ok: bool | None = None
    confidence: Confidence | None = None


class _Text(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    outcomes: tuple[_Outcome, ...]


class _Versions(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    eval: str
    catalog: str


class _Report(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str
    split: str
    versions: _Versions
    texts: tuple[_Text, ...]


@dataclass(frozen=True)
class Row:
    key: str  # "<text id>#<n>", as the reports and the benchmark name a claim
    run: str  # the report it came from
    group: str  # its cross-validation group (statistic and place)
    signals: Signals
    right: bool  # the verdict matched the label

    @property
    def x(self) -> list[float | None]:
        return vector(self.signals)


@dataclass(frozen=True)
class Dataset:
    rows: list[Row]
    reports: dict[str, str]  # report file name -> sha256
    eval_version: str
    catalog_version: str
    skipped: dict[str, int]  # why claims are not rows: "cant_check", "no verdict", ...


class DatasetError(Exception):
    """Reports that cannot be read together."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(paths: Sequence[Path], claims: Sequence[Claim], eval_version: str) -> Dataset:
    """Rows from every report in `paths`. Raises LeakageError if a report is not of the dev
    split or names a claim that is not a dev claim (every problem at once), and DatasetError if
    a report is of another benchmark version than `eval_version` (its labels may differ)."""
    if not paths:
        raise DatasetError("no evaluation report given: run `make eval` (the dev split) first")
    reports = [(p, _Report.model_validate_json(p.read_text(encoding="utf-8"))) for p in paths]
    names = [p.name for p, _ in reports]
    if len(set(names)) != len(names):
        raise DatasetError(f"two reports share a file name: {sorted(names)}")
    _check_held_out(reports, claims)
    stale = [
        f"{p.name}: eval {r.versions.eval}" for p, r in reports if r.versions.eval != eval_version
    ]
    if stale:
        raise DatasetError(
            f"reports of another benchmark version than {eval_version}: " + "; ".join(stale)
        )
    catalogs = sorted({r.versions.catalog for _, r in reports})
    by_key = {c.key: c for c in claims}
    rows: list[Row] = []
    skipped: dict[str, int] = {}
    for path, report in reports:
        for text in report.texts:
            for o in text.outcomes:
                key = f"{o.text_id}#{o.index + 1}"
                why = _not_a_row(o)
                if why is not None:
                    skipped[why] = skipped.get(why, 0) + 1
                    continue
                assert o.confidence is not None and o.verdict_ok is not None  # noqa: S101 (_not_a_row)
                rows.append(
                    Row(
                        key=key,
                        run=path.name,
                        group=by_key[key].group,
                        signals=o.confidence.signals,
                        right=o.verdict_ok,
                    )
                )
    return Dataset(
        rows=rows,
        reports={p.name: sha256_of(p) for p, _ in reports},
        eval_version=eval_version,
        catalog_version=", ".join(catalogs),
        skipped=dict(sorted(skipped.items())),
    )


def _not_a_row(o: _Outcome) -> str | None:
    """Why a claim gives no row, or None if it does."""
    if o.status != "scored" or o.verdict is None or o.verdict_ok is None:
        return "no verdict (not run, source down, or missed by extraction)"
    if o.verdict == CANT_CHECK:
        return "cant_check (nothing to abstain from)"
    if o.confidence is None:
        return "no signals (a report from before P4.5)"
    return None


def _check_held_out(reports: Sequence[tuple[Path, _Report]], claims: Sequence[Claim]) -> None:
    dev_keys = {c.key for c in claims if c.split == "dev"}
    held = {c.key for c in claims if c.split != "dev"}
    problems: list[str] = []
    for path, report in reports:
        if report.split != "dev":
            problems.append(f"{path.name}: a report of the {report.split!r} split, not 'dev'")
        for text in report.texts:
            for o in text.outcomes:
                key = f"{o.text_id}#{o.index + 1}"
                if key in held:
                    problems.append(f"{path.name}: {key} is a held-out claim")
                elif key not in dev_keys:
                    problems.append(f"{path.name}: {key} is not a claim of the benchmark")
    if problems:
        raise LeakageError(problems)
