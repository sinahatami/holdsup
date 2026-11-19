"""The part of a page HoldsUp checks: its paragraphs that state a figure, in page order, up to
the same length as a pasted text.

A whole article is longer than the claim extractor reads at once, and most of it states no
figure. So the paragraphs that do (a quantity, a share, or a change since a year) are kept,
long ones cut to their sentences with figures, repeats dropped, until the length runs out.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from holdsup.pipeline.numerals import written_numbers

LONG = 600  # characters; a longer paragraph keeps only its sentences with figures
MIN_CHARS = 25  # shorter lines with a figure are bylines, captions and dates, not claims
GAP = " … "  # marks sentences left out of a long paragraph

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
# Dates and times state no quantity: "12 March 2024", "March 12, 2024", "2024-03-12", "10:30".
_DATES = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+\d{{4}})?\b"
    rf"|\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"
    r"|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b|\b\d{1,2}:\d{2}\b",
    re.IGNORECASE,
)
# A figure written in words: "has halved", "twice as many", "a third of".
_WORD_FIGURE = re.compile(
    r"\b(?:half|halved|halving|twice|doubled|doubling|tripled|trebled|quadrupled|"
    r"a (?:third|quarter|fifth|tenth)|per ?cent|percent)\b",
    re.IGNORECASE,
)
# A change or comparison, which turns a bare year into a claim: "has risen since 2008".
_CHANGE = re.compile(
    r"\b(?:rose|risen|rises?|rising|fell|fallen|falls?|falling|grew|grown|grows?|growing|"
    r"dropped|drops?|climbed|jumped|surged|plunged|soared|slumped|increased?|increasing|"
    r"decreased?|decreasing|declined?|declining|higher|lower|highest|lowest|record|"
    r"more|fewer|less|since)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(?<=[.!?…])\s+(?=[\"“‘(\[]?[A-Z0-9])")


@dataclass(frozen=True)
class Excerpt:
    text: str
    used: int  # passages kept
    found: int  # passages with a figure on the page


def has_figure(text: str) -> bool:
    """True when `text` states a figure: a quantity that is not just a year or a date, a figure
    in words, or a year with a change ("has fallen since 2015")."""
    if len(text) < MIN_CHARS:
        return False
    undated = _DATES.sub(" ", text)
    numbers = written_numbers(undated)
    if any(not _is_year(n.text) for n in numbers) or _WORD_FIGURE.search(undated):
        return True
    return bool(numbers) and _CHANGE.search(undated) is not None


def _is_year(numeral: str) -> bool:
    return numeral.isdigit() and len(numeral) == 4 and 1800 <= int(numeral) <= 2100


def _shorten(paragraph: str, limit: int) -> str:
    if len(paragraph) > LONG:
        figures = [s for s in _SENTENCE.split(paragraph) if has_figure(s)]
        paragraph = GAP.join(figures) or paragraph
    if len(paragraph) <= limit:
        return paragraph
    cut = paragraph[: limit - 1]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut) + "…"


def excerpt(paragraphs: Iterable[str], limit: int) -> Excerpt:
    """The paragraphs with figures, in order, joined by blank lines, at most `limit` long.
    It stops at the first that no longer fits, so what is checked reads as the page does."""
    passages: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        if paragraph in seen or not has_figure(paragraph):
            continue
        seen.add(paragraph)
        passages.append(_shorten(paragraph, limit))
    kept: list[str] = []
    size = 0
    for passage in passages:
        size += len(passage) + (2 if kept else 0)
        if size > limit:
            break
        kept.append(passage)
    return Excerpt(text="\n\n".join(kept), used=len(kept), found=len(passages))
