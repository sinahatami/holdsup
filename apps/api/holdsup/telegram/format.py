"""A finished check, or why there is none, as one Telegram message (HTML).

Every figure in a message comes from the check's own text: the claim's quote and the
explanation, which the explain step already held to the computed results (golden rule 1).
Telegram allows 4,096 characters, so claims past the budget are left to the receipt.
"""

from html import escape

from holdsup.catalog.schema import Source
from holdsup.pipeline.result import ClaimResult
from holdsup.problems import Problem, pages_limited, rate_limited
from holdsup.service.store import CheckResult
from holdsup.telegram import strings

BUDGET = 3_800  # characters of HTML, under Telegram's 4,096 with room for the closing lines
MAX_QUOTE = 300  # a claim's quote longer than this is cut (the receipt has it whole)

_TOO_MANY_CHECKS = rate_limited(1).title
_TOO_MANY_LINKS = pages_limited(1).title


def text(value: str) -> str:
    return escape(value, quote=False)


def attr(value: str) -> str:
    return escape(value, quote=True)


def receipt_url(site: str, result: CheckResult) -> str:
    return f"{site}/check/{result.id}"


def _source(name: str) -> str:
    try:
        return Source(name).label
    except ValueError:
        return name


def claim_block(c: ClaimResult) -> str:
    quote = c.claim.quote if len(c.claim.quote) <= MAX_QUOTE else c.claim.quote[:MAX_QUOTE] + "…"
    lines = [
        f"<b>{text(strings.LABELS[c.verdict.label])}</b>",
        f"“{text(quote)}”",
        text(c.explanation),
    ]
    if c.indicator is not None and c.data is not None:
        lines.append(
            strings.SOURCE.format(
                indicator=text(c.indicator.name), source=text(_source(c.data.source))
            )
        )
    return "\n".join(lines)


def result_message(result: CheckResult, site: str) -> str:
    if not result.claims:
        return strings.NO_CLAIMS.format(example=text(strings.EXAMPLE))
    head = []
    if result.page is not None:
        title = result.page.title or result.page.url
        head.append(strings.FROM_PAGE.format(url=attr(result.page.url), title=text(title)))
    blocks: list[str] = []
    used = sum(len(h) for h in head)
    for c in result.claims:
        block = claim_block(c)
        if blocks and used + len(block) > BUDGET:
            break
        blocks.append(block)
        used += len(block) + 2
    tail = []
    if left := len(result.claims) - len(blocks):
        tail.append(strings.MORE_CLAIMS.format(n=left))
    tail.append(strings.RECEIPT.format(url=attr(receipt_url(site, result))))
    return "\n\n".join([*head, *blocks, "\n".join(tail)])


def problem_message(problem: Problem) -> str:
    """Why a message was not checked, in the bot's words where the site's would not fit
    ("this address" is a browser's; here it is the person)."""
    wait = strings.minutes(problem.retry_after)
    if problem.title == _TOO_MANY_CHECKS:
        return strings.TOO_MANY_CHECKS.format(minutes=wait)
    if problem.title == _TOO_MANY_LINKS:
        return strings.TOO_MANY_LINKS.format(minutes=wait)
    if problem.status >= 500 and problem.type == "/problems/internal":
        return strings.FAILED
    return text(problem.detail or problem.title)
