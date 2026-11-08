"""Read the numbers a text writes, so code can drop any number the model made up."""

import re
from collections.abc import Iterable

WORD_NUMBERS = {
    "half": 0.5,
    "halved": 0.5,
    "halve": 0.5,
    "double": 2.0,
    "doubled": 2.0,
    "twice": 2.0,
    "triple": 3.0,
    "tripled": 3.0,
    "trebled": 3.0,
    "quadrupled": 4.0,
    **{
        w: float(i)
        for i, w in enumerate(
            [
                "zero",
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
                "ten",
                "eleven",
                "twelve",
            ]
        )
    },
}


def readings(text: str) -> list[set[float]]:
    """Each number the text writes, as the set of values it can mean (either decimal mark:
    "6,1" and "1,000"; "halved" is 0.5)."""
    out: list[set[float]] = []
    for token in re.findall(r"\d+(?:[.,]\d+)*", text):
        values = set()
        for candidate in (token.replace(",", ""), token.replace(".", "").replace(",", ".")):
            try:
                values.add(float(candidate))
            except ValueError:
                continue
        out.append(values)
    out.extend(
        {WORD_NUMBERS[w]} for w in re.findall(r"[a-z]+", text.casefold()) if w in WORD_NUMBERS
    )
    return out


def numbers_in(text: str) -> set[float]:
    """Every number the text writes."""
    return set().union(*readings(text))


def is_among(value: float, numbers: Iterable[float]) -> bool:
    """Whether `value` equals one of `numbers` (up to float rounding)."""
    return any(abs(value - n) <= 1e-9 * max(1.0, abs(n)) for n in numbers)


def times_written(value: float, text: str) -> int:
    return sum(1 for values in readings(text) if is_among(value, values))
