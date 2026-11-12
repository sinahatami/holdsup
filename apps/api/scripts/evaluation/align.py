"""Which extracted claim is which labelled claim.

A person labels the claims in a text; the extractor returns its own list, in its own order and
with its own quotes. They are paired one to one by how much of their quotes overlap, so that
extraction precision and recall, and every later step, are scored on the right claim.

Overlap is the share of the shorter quote's words (stop words dropped) found in the other, so
a whole sentence extracted as one quote still covers a short labelled fragment. Two labelled
claims can still not share one extracted claim: a merged claim is a missed one, because only
one of them gets a verdict. Ties go to the pair that agrees on place and window.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from holdsup.pipeline.claim import ClaimSpec
from scripts.evaluation.benchmark import LabelledClaim

MIN_OVERLAP = 0.6

WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "since",
        "than",
        "the",
        "to",
        "was",
        "were",
        "with",
    ]
)


def words(quote: str) -> frozenset[str]:
    return frozenset(w for w in WORD.findall(quote.lower()) if w not in STOP_WORDS)


def overlap(a: str, b: str) -> float:
    """Share of the shorter quote's words that the other quote has; 0 if either has none."""
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def period_ok(expected: str, got: str | None) -> bool:
    """A labelled period against the extracted one. A bare year also accepts a month or
    quarter in that year; anything finer than a year must match exactly."""
    if got is None:
        return False
    if expected == got:
        return True
    return len(expected) == 4 and got[:4] == expected


def geo_ok(label: LabelledClaim, claim: ClaimSpec) -> bool:
    return label.geo == claim.geo


def start_ok(label: LabelledClaim, claim: ClaimSpec) -> bool:
    # A level claim ("debt is 133% in 2013") may leave its start empty: it is its end.
    return period_ok(label.window[0], claim.start if claim.start is not None else claim.end)


def end_ok(label: LabelledClaim, claim: ClaimSpec) -> bool:
    return period_ok(label.window[1], claim.end)


@dataclass(frozen=True)
class Link:
    label: int  # index into the labelled claims
    extracted: int  # index into the extracted claims
    overlap: float


def align(labelled: Sequence[LabelledClaim], extracted: Sequence[ClaimSpec]) -> list[Link]:
    """One-to-one links between labelled and extracted claims, best overlap first."""
    candidates: list[tuple[float, int, int, int]] = []
    for i, label in enumerate(labelled):
        for j, claim in enumerate(extracted):
            score = overlap(label.quote, claim.quote)
            if score >= MIN_OVERLAP:
                agreement = geo_ok(label, claim) + start_ok(label, claim) + end_ok(label, claim)
                candidates.append((-score, -agreement, i, j))
    links: list[Link] = []
    used_labels: set[int] = set()
    used_extracted: set[int] = set()
    for negative_score, _, i, j in sorted(candidates):
        if i in used_labels or j in used_extracted:
            continue
        used_labels.add(i)
        used_extracted.add(j)
        links.append(Link(label=i, extracted=j, overlap=round(-negative_score, 3)))
    return sorted(links, key=lambda link: link.label)
