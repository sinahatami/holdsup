"""How good a probability of "the verdict is right" is: Brier score, log loss, AUC, the
calibration curve, the accuracy-versus-coverage curve, and the abstention threshold.

Plain numpy, so the figures are the same whichever model made the probabilities.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

EPS = 1e-12
Floats = npt.NDArray[np.float64]


def _arrays(y: Sequence[bool] | Sequence[int], p: Sequence[float]) -> tuple[Floats, Floats]:
    ya = np.asarray(y, dtype=np.float64)
    pa = np.asarray(p, dtype=np.float64)
    if ya.shape != pa.shape or ya.ndim != 1 or not len(ya):
        raise ValueError("labels and probabilities must be two lists of the same, non-zero length")
    return ya, pa


def brier(y: Sequence[bool] | Sequence[int], p: Sequence[float]) -> float:
    """Mean squared gap between the probability and what happened (0 is perfect)."""
    ya, pa = _arrays(y, p)
    return float(np.mean((pa - ya) ** 2))


def log_loss(y: Sequence[bool] | Sequence[int], p: Sequence[float]) -> float:
    ya, pa = _arrays(y, p)
    pa = np.clip(pa, EPS, 1 - EPS)
    return float(-np.mean(ya * np.log(pa) + (1 - ya) * np.log(1 - pa)))


def auc(y: Sequence[bool] | Sequence[int], p: Sequence[float]) -> float | None:
    """The chance a right verdict scores above a wrong one (ties count half); None when the
    labels are all one kind."""
    ya, pa = _arrays(y, p)
    pos, neg = pa[ya == 1], pa[ya == 0]
    if not len(pos) or not len(neg):
        return None
    above = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(above / (len(pos) * len(neg)))


@dataclass(frozen=True)
class Bin:
    low: float
    high: float
    n: int
    mean_probability: float | None  # None for an empty bin
    accuracy: float | None


def calibration(y: Sequence[bool] | Sequence[int], p: Sequence[float], bins: int = 5) -> list[Bin]:
    """Equal-width bins over [0, 1]: in each, the mean probability against the share right.
    A calibrated model's two numbers are close."""
    ya, pa = _arrays(y, p)
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    for i in range(bins):
        last = i == bins - 1
        inside = (pa >= edges[i]) & ((pa <= edges[i + 1]) if last else (pa < edges[i + 1]))
        n = int(inside.sum())
        out.append(
            Bin(
                low=round(float(edges[i]), 4),
                high=round(float(edges[i + 1]), 4),
                n=n,
                mean_probability=float(pa[inside].mean()) if n else None,
                accuracy=float(ya[inside].mean()) if n else None,
            )
        )
    return out


@dataclass(frozen=True)
class CoveragePoint:
    answered: int  # claims answered: the `answered` most confident
    coverage: float  # their share of all claims
    accuracy: float  # of the answered
    lowest: float  # the lowest probability answered


def coverage_curve(y: Sequence[bool] | Sequence[int], p: Sequence[float]) -> list[CoveragePoint]:
    """Answer the most confident claims first: accuracy as coverage grows. Claims with equal
    probabilities are answered together (a threshold cannot split them)."""
    ya, pa = _arrays(y, p)
    order = np.argsort(-pa, kind="stable")
    ys, ps = ya[order], pa[order]
    out = []
    n = len(ys)
    for k in range(1, n + 1):
        if k < n and ps[k] == ps[k - 1]:
            continue  # a tie with the next claim: it is answered too
        out.append(
            CoveragePoint(
                answered=k,
                coverage=k / n,
                accuracy=float(ys[:k].mean()),
                lowest=float(ps[k - 1]),
            )
        )
    return out


@dataclass(frozen=True)
class Threshold:
    threshold: float  # answer when the probability is at least this
    target: float
    met: bool  # some coverage reached the target accuracy
    answered: int
    coverage: float
    accuracy: float  # of the answered (the target or above when met)


def choose_threshold(
    y: Sequence[bool] | Sequence[int], p: Sequence[float], target: float
) -> Threshold:
    """The cut-off that answers the most claims while their accuracy stays at `target` or above.
    It sits halfway between the lowest probability answered and the next one down, so a claim
    scored just like a training claim falls on the same side. When no coverage reaches the
    target the most accurate one is used, and `met` says so; when every claim can be answered
    the threshold is 0 (never abstain)."""
    ya, pa = _arrays(y, p)
    curve = coverage_curve(ya.tolist(), pa.tolist())
    meeting = [c for c in curve if c.accuracy >= target]
    met = bool(meeting)
    pick = (
        max(meeting, key=lambda c: c.answered)
        if meeting
        else max(curve, key=lambda c: (c.accuracy, c.answered))
    )
    below = pa[pa < pick.lowest]
    threshold = 0.0 if not len(below) else (pick.lowest + float(below.max())) / 2
    return Threshold(
        threshold=threshold,
        target=target,
        met=met,
        answered=pick.answered,
        coverage=pick.coverage,
        accuracy=pick.accuracy,
    )
