"""The readable text of a page: the story's paragraphs, never its furniture."""

from pathlib import Path

from holdsup.page.text import read_html

LEAD = (
    "Italy's youth unemployment rate fell from 40.3% in 2015 to 20.3% in 2023, the "
    "statistics office said on Tuesday."
)
EMPLOYMENT = (
    "Employment among those aged 15 to 24 rose by 300,000 over the same period, while the "
    "number of young people not in work or education fell."
)

ARTICLE = (Path(__file__).parents[1] / "fixtures" / "pages" / "article.html").read_text()


def test_only_the_story_is_read_without_furniture_scripts_or_hidden_parts() -> None:
    page = read_html(ARTICLE)
    assert page.paragraphs == [
        LEAD,
        "The minister welcomed the news at a press conference in Rome.",
        "Source: national statistics office",
        EMPLOYMENT,
        "Critics say the figure has been falling since 2014 & that the trend began earlier.",
        LEAD,
    ]


def test_the_title_is_the_pages_own_headline_else_its_title_tag() -> None:
    assert read_html(ARTICLE).title == "Youth unemployment in Italy has halved since 2015"
    plain = "<html><head><title> Jobs \n report </title></head><body><p>x</p></body></html>"
    assert read_html(plain).title == "Jobs report"
    assert read_html("<p>No title here at all.</p>").title is None


def test_a_page_without_a_marked_story_is_read_whole() -> None:
    html = """<body><div><p>First paragraph with 12% in it.</p>
    <div>Second, in a bare div, with 3 million.</div></div><nav>Menu 1 2 3</nav></body>"""
    assert read_html(html).paragraphs == [
        "First paragraph with 12% in it.",
        "Second, in a bare div, with 3 million.",
    ]


def test_a_short_marked_story_is_a_teaser_so_the_whole_page_is_read() -> None:
    html = "<article><p>Teaser 5%.</p></article><div><p>The full text says 7%.</p></div>"
    assert read_html(html).paragraphs == ["Teaser 5%.", "The full text says 7%."]


def test_role_main_marks_the_story_and_nested_elements_of_its_kind_stay_inside() -> None:
    body = "Inside the story, with enough words to be a story of its own. " * 4
    html = f"""<div>Outside before</div>
    <div role="main"><div><p>{body}</p></div><div>Still inside</div></div>
    <div>Outside after</div>"""
    assert read_html(html).paragraphs == [body.strip(), "Still inside"]


def test_a_skipped_element_ends_where_its_own_tag_closes_even_when_nested() -> None:
    html = """<p>Before</p><aside><aside>inner</aside><p>still aside</p></aside><p>After</p>
    <div hidden><div>gone</div><div>gone too</div></div><p>Last</p>"""
    assert read_html(html).paragraphs == ["Before", "After", "Last"]


def test_self_closing_tags_and_unclosed_paragraphs() -> None:
    html = '<meta property="og:title" content="T"/><p>One<br/>Two<p>Three<hr/>Four'
    page = read_html(html)
    assert page.title == "T"
    assert page.paragraphs == ["One Two", "Three", "Four"]


def test_a_long_title_is_cut() -> None:
    assert len(read_html(f"<title>{'x' * 500}</title>").title or "") == 300


def test_tables_and_reference_marks_are_left_out() -> None:
    html = """<table class="infobox"><caption>Economy</caption>
    <tr><th>GDP</th><td>$2.7 trillion (2026)[7]</td></tr></table>
    <p>Milan is the main economic centre of Italy.[1]</p>
    <p>Debt reached 137% of GDP in 2023.[12][a][citation needed]</p>"""
    assert read_html(html).paragraphs == [
        "Milan is the main economic centre of Italy.",
        "Debt reached 137% of GDP in 2023.",
    ]
