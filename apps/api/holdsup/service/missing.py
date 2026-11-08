"""What people ask HoldsUp to check that it cannot: the data behind `make missing-report`.

Reads stored results, groups the claims that came back "can't check" by the topic the claim
names (its indicator phrase), and ranks the topics. The grouping is by words, not meaning:
"gender pay gap" and "women's pay gap" are two topics, so read the list as a guide to what to
add to the catalog, not as a census.
"""

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from holdsup.service.store.model import CheckResult
from holdsup.verdict.model import Label

_NOT_WORD = re.compile(r"[^\w]+")
EXAMPLE_CHARS = 100


@dataclass(frozen=True)
class Topic:
    topic: str  # the most common wording in the group
    claims: int
    checks: int  # how many different checks asked about it
    unmatched: int  # claims for which no statistic matched at all
    closest: str | None  # the statistic most often offered instead
    example: str  # the quote of the newest claim


@dataclass(frozen=True)
class Report:
    topics: list[Topic]
    checks_read: int
    unreadable: int  # stored results this version of the code cannot read
    cant_check: int  # claims counted: can't-check, not a passing outage


def topic_key(phrase: str) -> str:
    """The wording with case, punctuation and spacing removed, so small variations group."""
    return _NOT_WORD.sub(" ", phrase.casefold()).strip()


def summarize(results: Iterable[Mapping[str, Any]], limit: int = 20) -> Report:
    """Rank the topics of can't-check claims, most frequent first (ties: A to Z).

    A claim that failed because a source was briefly down (`retryable`) is left out: nothing
    is missing from the catalog for it.
    """
    wording: dict[str, Counter[str]] = {}
    checks: dict[str, set[object]] = {}
    unmatched: Counter[str] = Counter()
    closest: dict[str, Counter[str]] = {}
    newest: dict[str, tuple[str, str]] = {}  # key -> (created_at, quote)
    read = unreadable = counted = 0
    for raw in results:
        try:
            result = CheckResult.model_validate(raw)
        except ValidationError:
            unreadable += 1
            continue
        read += 1
        for claim in result.claims:
            if claim.verdict.label is not Label.CANT_CHECK or claim.retryable:
                continue
            key = topic_key(claim.claim.indicator_phrase)
            if not key:
                continue
            counted += 1
            wording.setdefault(key, Counter())[claim.claim.indicator_phrase.strip()] += 1
            checks.setdefault(key, set()).add(result.id)
            if claim.indicator is None:
                unmatched[key] += 1
            if claim.suggestions:
                closest.setdefault(key, Counter())[claim.suggestions[0].name] += 1
            stamp = result.created_at.isoformat()
            if key not in newest or stamp > newest[key][0]:
                newest[key] = (stamp, claim.claim.quote)
    topics = [
        Topic(
            topic=wording[key].most_common(1)[0][0],
            claims=sum(wording[key].values()),
            checks=len(checks[key]),
            unmatched=unmatched[key],
            closest=closest[key].most_common(1)[0][0] if key in closest else None,
            example=newest[key][1],
        )
        for key in wording
    ]
    topics.sort(key=lambda t: (-t.claims, t.topic.casefold()))
    return Report(topics[:limit], checks_read=read, unreadable=unreadable, cant_check=counted)


def format_report(report: Report) -> str:
    """The report as plain text for a terminal."""
    head = (
        f"{report.cant_check} can't-check claims in {report.checks_read} finished checks"
        " (answers copied from the ledger and passing source outages are left out)"
    )
    if report.unreadable:
        head += f"; {report.unreadable} stored results could not be read"
    if not report.topics:
        return head + "\nNothing to add: no can't-check claims yet.\n"
    lines = [head, "", "Most frequent topics:"]
    for rank, t in enumerate(report.topics, 1):
        claims = f"{t.claims} claim{'' if t.claims == 1 else 's'}"
        checks = f"{t.checks} check{'' if t.checks == 1 else 's'}"
        lines.append(f"{rank:>3}. {t.topic}  ({claims} in {checks})")
        lines.append(f"       no statistic matched: {t.unmatched} of {t.claims}")
        if t.closest:
            lines.append(f"       closest offered: {t.closest}")
        example = t.example if len(t.example) <= EXAMPLE_CHARS else t.example[:EXAMPLE_CHARS] + "…"
        lines.append(f'       e.g. "{example}"')
    return "\n".join(lines) + "\n"
