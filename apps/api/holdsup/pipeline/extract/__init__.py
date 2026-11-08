"""Step 2, extract claims: one model call returns raw fields, code turns them into `ClaimSpec`s.

The model only reads the text. Code resolves relative periods ("since I took office" from
office_terms.yaml, "in the past 19 years" counted back from when it was said), normalizes
codes and periods, and drops any asserted number that does not appear in the text.

Modules: `prompt` (the model call's schema and messages), `numbers` and `dates` (reading the
text), `resolve` (model answer → `ClaimSpec`).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.extract.dates import (
    MONTHS,
    SaidOn,
    attribution_date,
    normalize_period,
    parse_said_on,
)
from holdsup.pipeline.extract.numbers import WORD_NUMBERS, numbers_in, times_written
from holdsup.pipeline.extract.prompt import (
    EXTRACT_SYSTEM,
    Lookback,
    ModelClaim,
    ModelExtraction,
    Office,
    extract_messages,
)
from holdsup.pipeline.extract.resolve import VAGUE_RE, normalize_geo, operator_in, resolve
from holdsup.pipeline.terms import OfficeTerms
from holdsup.router import Attempt, Router, Use

__all__ = [
    "EXTRACT_SYSTEM",
    "MONTHS",
    "VAGUE_RE",
    "WORD_NUMBERS",
    "ExtractResult",
    "Lookback",
    "ModelClaim",
    "ModelExtraction",
    "Office",
    "SaidOn",
    "attribution_date",
    "extract_claims",
    "extract_messages",
    "normalize_geo",
    "normalize_period",
    "numbers_in",
    "operator_in",
    "parse_said_on",
    "resolve",
    "times_written",
]


@dataclass(frozen=True)
class ExtractResult:
    claims: list[ClaimSpec]
    raw: ModelExtraction  # the model's answer, kept for the trace
    content: str | None  # the raw response text
    provider: str
    model: str
    attempts: tuple[Attempt, ...]


async def extract_claims(
    router: Router,
    text: str,
    *,
    use: Use = Use.LIVE,
    said_on: str | None = None,
    today: date | None = None,
    terms: OfficeTerms | None = None,
) -> ExtractResult:
    """Extract every claim in `text`. Raises RouterError when no provider returns a valid
    answer."""
    result = await router.complete(
        "extract", extract_messages(text), use=use, schema=ModelExtraction
    )
    raw = result.parsed or ModelExtraction(speaker=None, said_on=None, claims=[])
    # The caller's date beats a written attribution, which beats the model's reading.
    said = parse_said_on(
        said_on or attribution_date(text) or raw.said_on, today or datetime.now(UTC).date()
    )
    claims = [
        resolve(c, text=text, speaker=raw.speaker, said=said, terms=terms) for c in raw.claims
    ]
    return ExtractResult(
        claims=claims,
        raw=raw,
        content=result.content,
        provider=result.provider,
        model=result.model,
        attempts=result.attempts,
    )
