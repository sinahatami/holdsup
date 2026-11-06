"""Change between two values of a series (CLAUDE.md golden rule 1: arithmetic lives here)."""

from enum import StrEnum


class ChangeKind(StrEnum):
    ABSOLUTE = "absolute"  # end - start, in the series' unit
    PERCENT = "percent"  # relative change, in % of the start value
    PERCENTAGE_POINTS = "percentage_points"  # end - start, for series already in %
    RATIO = "ratio"  # end / start


def change(start: float, end: float, kind: ChangeKind) -> float:
    """Change from `start` to `end`. Percent and ratio need a non-zero start."""
    if kind in (ChangeKind.ABSOLUTE, ChangeKind.PERCENTAGE_POINTS):
        return end - start
    if start == 0:
        raise ValueError(f"{kind} change is undefined for a start value of 0")
    if kind is ChangeKind.PERCENT:
        return (end - start) / abs(start) * 100
    return end / start
