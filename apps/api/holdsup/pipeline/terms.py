"""Terms of office: resolve "since I took office" to a date in code, not from model memory."""

import re
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

OFFICE_TERMS = Path(__file__).with_name("office_terms.yaml")


class Term(BaseModel):
    start: date
    end: date | None = None  # None = still in office


class Holder(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    country: str
    office: str
    terms: list[Term]


class OfficeTerms(BaseModel):
    holders: list[Holder]


def _words(text: str) -> tuple[str, ...]:
    """Casefolded words without accents or punctuation: 'Pedro Sánchez' -> ('pedro', 'sanchez')."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return tuple(re.findall(r"[a-z0-9]+", plain.casefold()))


def _contains(words: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    n = len(phrase)
    return n > 0 and any(words[i : i + n] == phrase for i in range(len(words) - n + 1))


@lru_cache
def load_office_terms(path: Path = OFFICE_TERMS) -> OfficeTerms:
    return OfficeTerms.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def find_holders(
    who: str, country: str | None = None, terms: OfficeTerms | None = None
) -> list[Holder]:
    """Holders whose name or an alias appears as whole words in `who` ("President Trump")."""
    words = _words(who)
    found = [
        h
        for h in (terms or load_office_terms()).holders
        if any(_contains(words, _words(n)) for n in (h.name, *h.aliases))
        and (country is None or h.country == country)
    ]
    return found


def pick_term(holder: Holder, said_by: date, *, previous: bool) -> Term | None:
    """The term the claim refers to: the latest one started by `said_by`; with `previous`,
    the latest one that had already ended by then ("the last Labour government")."""
    started = [t for t in holder.terms if t.start <= said_by]
    if previous:
        started = [t for t in started if t.end is not None and t.end <= said_by]
    return max(started, key=lambda t: t.start, default=None)
