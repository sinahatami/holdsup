"""Ranking figures over the candidates shown for each claim: top-1, recall@k, MRR@k, margins.

Both rankers order the same top-8 list, so recall@8 is the search's ceiling and equal for
both; top-1 and MRR@8 are where reordering shows. A claim the catalog has nothing for has no
right answer: it is left out of top-1 and MRR, and counts as wrong in the margin table if its
margin is wide enough to skip the model (picking anything would be wrong).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel

K = 8


@dataclass(frozen=True)
class Ranked:
    claim: str  # claim key
    gold: str | None
    ids: tuple[str, ...]  # best first
    scores: tuple[float, ...]  # same order, higher is better
    seen: bool  # the gold indicator was in the training data of the model that ranked this

    @property
    def margin(self) -> float:
        """How far the first is ahead of the second (the first's score when alone)."""
        if not self.scores:
            return 0.0
        return self.scores[0] - (self.scores[1] if len(self.scores) > 1 else 0.0)


def rank(claim: str, gold: str | None, ids: Sequence[str], scores: Sequence[float], *,
         seen: bool) -> Ranked:  # fmt: skip
    """Order `ids` by `scores`, best first; ties keep the given (search) order."""
    order = sorted(range(len(ids)), key=lambda i: -scores[i])
    return Ranked(claim, gold, tuple(ids[i] for i in order), tuple(scores[i] for i in order), seen)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def reciprocal_rank(r: Ranked, k: int = K) -> float:
    if r.gold is None or r.gold not in r.ids[:k]:
        return 0.0
    return 1.0 / (r.ids.index(r.gold) + 1)


class Summary(BaseModel):
    claims: int  # with a labelled indicator
    top1: float | None
    recall_at_8: float | None
    mrr_at_8: float | None


def summarize(rows: Sequence[Ranked]) -> Summary:
    scored = [r for r in rows if r.gold is not None]
    n = len(scored)
    if not n:
        return Summary(claims=0, top1=None, recall_at_8=None, mrr_at_8=None)
    return Summary(
        claims=n,
        top1=sum(bool(r.ids) and r.ids[0] == r.gold for r in scored) / n,
        recall_at_8=sum(r.gold in r.ids[:K] for r in scored) / n,
        mrr_at_8=sum(reciprocal_rank(r) for r in scored) / n,
    )


class MarginRow(BaseModel):
    threshold: float
    answered: int  # claims whose margin is at least the threshold (the model call is skipped)
    coverage: float  # answered / all claims
    correct: int  # answered claims whose first candidate is the labelled indicator
    accuracy: float | None  # correct / answered


def margin_table(rows: Sequence[Ranked], thresholds: Sequence[float]) -> list[MarginRow]:
    out: list[MarginRow] = []
    for t in thresholds:
        answered = [r for r in rows if r.ids and r.margin >= t]
        correct = sum(r.gold is not None and r.ids[0] == r.gold for r in answered)
        out.append(
            MarginRow(
                threshold=t,
                answered=len(answered),
                coverage=len(answered) / len(rows) if rows else 0.0,
                correct=correct,
                accuracy=correct / len(answered) if answered else None,
            )
        )
    return out
