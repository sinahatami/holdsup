"""What part of a page is checked: its passages with figures, in order, within the length cap."""

from pathlib import Path

import pytest

from holdsup.page.excerpt import GAP, LONG, excerpt, has_figure
from holdsup.page.text import read_html

LEAD = (
    "Italy's youth unemployment rate fell from 40.3% in 2015 to 20.3% in 2023, the "
    "statistics office said on Tuesday."
)
EMPLOYMENT = (
    "Employment among those aged 15 to 24 rose by 300,000 over the same period, while the "
    "number of young people not in work or education fell."
)


@pytest.mark.parametrize(
    "text",
    [
        "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
        "Employment rose by 300,000 people over the same period.",
        "Public debt reached 1.7 trillion euros last year, the office said.",
        "Youth unemployment in Italy has halved since the crisis began.",
        "Twice as many people now work from home as did before.",
        "Unemployment has risen every year since 2008, the union claims.",
        "A third of young adults still live with their parents today.",
    ],
)
def test_a_figure_is_a_quantity_a_figure_in_words_or_a_year_with_a_change(text: str) -> None:
    assert has_figure(text)


@pytest.mark.parametrize(
    "text",
    [
        "By A. Writer, published 12 March 2024 at 10:30, updated March 13, 2024.",
        "The minister welcomed the news at a press conference in Rome.",
        "The law was passed in 2015 after a long debate in parliament.",
        "Updated on 2024-03-12 and again on 13/03/2024 by the desk.",
        "Prices 5%",  # too short to be a claim
    ],
)
def test_dates_years_alone_and_short_lines_are_not_figures(text: str) -> None:
    assert not has_figure(text)


def test_the_article_fixture_keeps_its_figures_once_and_in_order() -> None:
    page = read_html(
        (Path(__file__).parents[1] / "fixtures" / "pages" / "article.html").read_text()
    )
    cut = excerpt(page.paragraphs, 2_000)
    assert cut.text.split("\n\n") == [
        LEAD,
        EMPLOYMENT,
        "Critics say the figure has been falling since 2014 & that the trend began earlier.",
    ]
    assert (cut.used, cut.found) == (3, 3)


def test_it_stops_at_the_first_passage_that_no_longer_fits() -> None:
    first, second, third = (f"Paragraph {n} says prices rose {n}% last year." for n in (1, 2, 3))
    limit = len(first) + 2 + len(second)
    cut = excerpt([first, second, third], limit)
    assert cut.text == f"{first}\n\n{second}"
    assert (cut.used, cut.found) == (2, 3)
    assert len(cut.text) == limit


def test_a_long_paragraph_keeps_only_its_sentences_with_figures() -> None:
    filler = "This sentence only sets the scene for the reader and states nothing at all. "
    paragraph = (
        filler * 4
        + "Debt rose to 137% of GDP in 2023. "
        + filler * 4
        + "Growth was 0.9% that year."
    )
    assert len(paragraph) > LONG
    cut = excerpt([paragraph], 2_000)
    assert cut.text == f"Debt rose to 137% of GDP in 2023.{GAP}Growth was 0.9% that year."


def test_a_passage_longer_than_the_cap_is_cut_at_a_word() -> None:
    sentence = "Exports grew 4% while imports grew 2% and the balance improved further "
    cut = excerpt([sentence * 40], 200)
    assert cut.used == 1
    assert len(cut.text) <= 200 and cut.text.endswith("…")
    assert not cut.text[:-1].endswith(" ")
    assert excerpt(["Exports grew 4% in " + "x" * 300], 100).text.endswith("…")


def test_nothing_with_a_figure_gives_an_empty_excerpt() -> None:
    cut = excerpt(["The minister welcomed the news at a press conference in Rome."], 2_000)
    assert (cut.text, cut.used, cut.found) == ("", 0, 0)
