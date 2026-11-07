"""Terms of office: the lookup that replaces the model's memory of who governed when."""

from datetime import date

import pytest

from holdsup.pipeline.terms import (
    Holder,
    OfficeTerms,
    Term,
    find_holders,
    load_office_terms,
    pick_term,
)


def test_office_terms_file_is_consistent() -> None:
    terms = load_office_terms()
    assert len(terms.holders) >= 30
    for holder in terms.holders:
        assert holder.terms, holder.name
        for term in holder.terms:
            assert term.end is None or term.start < term.end, holder.name
        starts = [t.start for t in holder.terms]
        assert starts == sorted(starts), holder.name
        assert sum(t.end is None for t in holder.terms) <= 1, holder.name
    names = [h.name for h in terms.holders]
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    ("who", "country", "expected"),
    [("President Trump", None, ["Donald Trump"]), ("Labour government", None, ["Labour Party"]),
     ("the Tories", "GB", ["Conservative Party"]), ("Pedro Sanchez", None, ["Pedro Sánchez"]),
     ("Sánchez", None, ["Pedro Sánchez"]), ("Renzi", "FR", []), ("Theresa", None, []),
     ("Trumpism", None, [])],
)  # fmt: skip
def test_find_holders(who: str, country: str | None, expected: list[str]) -> None:
    assert [h.name for h in find_holders(who, country)] == expected


def test_find_holders_with_an_injected_table() -> None:
    table = OfficeTerms(
        holders=[
            Holder(name="A B", country="XX", office="pm", terms=[Term(start=date(2000, 1, 1))])
        ]
    )
    assert [h.name for h in find_holders("a b", terms=table)] == ["A B"]


def test_pick_term() -> None:
    [trump] = find_holders("Trump")
    assert pick_term(trump, date(2026, 8, 31), previous=False) == trump.terms[1]
    assert pick_term(trump, date(2019, 1, 1), previous=False) == trump.terms[0]
    assert pick_term(trump, date(2026, 8, 31), previous=True) == trump.terms[0]
    assert pick_term(trump, date(2016, 1, 1), previous=False) is None
    [labour] = find_holders("Labour")
    assert pick_term(labour, date(2026, 11, 7), previous=True) == labour.terms[0]
