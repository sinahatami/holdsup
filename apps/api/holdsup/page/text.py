"""The readable text of an HTML page: its title and its paragraphs, in order.

Plain `html.parser` (no new dependency): scripts, styles, navigation, headers, footers, asides,
forms and hidden parts are skipped; every block element ends a paragraph. When the page marks
its story (<article>, <main> or role="main") and that holds enough text, only the story is
kept, so menus and "most read" lists left outside it never reach the claim extractor.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

MIN_STORY_CHARS = 200  # a marked story shorter than this is a teaser: read the whole page
MAX_TITLE = 300

# Never read: code, styling, page furniture, controls, embedded documents, and tables (an
# infobox or a data table holds figures, not claims: a claim is a sentence). (<head> is read:
# it holds the <title>; its scripts and styles are skipped like any others.)
_SKIP = frozenset(
    [
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "math",
        "canvas",
        "iframe",
        "object",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "select",
        "textarea",
        "dialog",
        "table",
    ]
)
# Each of these starts and ends a paragraph.
_BLOCKS = frozenset(
    [
        "p",
        "div",
        "section",
        "article",
        "main",
        "li",
        "ul",
        "ol",
        "dl",
        "dt",
        "dd",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        "figure",
        "figcaption",
        "address",
        "details",
        "summary",
        "hr",
    ]
)
_STORY = frozenset({"article", "main"})
_VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    ]
)
_SPACE = re.compile(r"\s+")
# Reference marks: "[7]", "[a]", "[citation needed]", "[note 3]". They would read as figures.
_NOTE_MARKS = re.compile(r"\[(?:\d+|[a-z]|note \d+|citation needed)\]", re.IGNORECASE)


@dataclass(frozen=True)
class Page:
    title: str | None
    paragraphs: list[str]


def read_html(html: str) -> Page:
    reader = _Reader()
    reader.feed(html)
    reader.close()
    story = [p for p, in_story in reader.blocks if in_story]
    if sum(len(p) for p in story) >= MIN_STORY_CHARS:
        paragraphs = story
    else:
        paragraphs = [p for p, _ in reader.blocks]
    title = reader.og_title or _clean(" ".join(reader.title_parts))
    return Page(title=title[:MAX_TITLE] or None, paragraphs=paragraphs)


def _clean(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def _hidden(attrs: dict[str, str | None]) -> bool:
    return "hidden" in attrs or (attrs.get("aria-hidden") or "").lower() == "true"


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, bool]] = []  # (paragraph, inside the story)
        self.title_parts: list[str] = []
        self.og_title = ""
        self._text: list[str] = []
        self._skip_tag: str | None = None  # the element being skipped, and how deep
        self._skip_depth = 0
        self._story_tag: str | None = None  # the outermost story element, and how deep
        self._story_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_tag is not None:
            if tag == self._skip_tag:
                self._skip_depth += 1
            return
        found = dict(attrs)
        if tag == "meta" and (found.get("property") or "").lower() == "og:title":
            self.og_title = _clean(found.get("content") or "")[:MAX_TITLE]
        if tag == "title":
            self._in_title = True
            return
        if tag in _VOID:
            self._void(tag)
            return
        if tag in _SKIP or _hidden(found):
            self._flush()
            self._skip_tag, self._skip_depth = tag, 1
            return
        if tag in _BLOCKS:
            self._flush()
        if tag == self._story_tag:
            self._story_depth += 1
        elif self._story_tag is None and (
            tag in _STORY or (found.get("role") or "").lower() == "main"
        ):
            self._story_tag, self._story_depth = tag, 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_tag is None and tag == "meta":
            self.handle_starttag(tag, attrs)
        elif self._skip_tag is None:
            self._void(tag)

    def _void(self, tag: str) -> None:
        # A line break stays inside its paragraph; a rule or a block ends it.
        if tag == "br":
            self._text.append(" ")
        elif tag in _BLOCKS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if self._skip_tag is not None:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in _BLOCKS:
            self._flush()
        if tag == self._story_tag:
            self._flush()
            self._story_depth -= 1
            if self._story_depth == 0:
                self._story_tag = None

    def handle_data(self, data: str) -> None:
        if self._skip_tag is not None:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self._text.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        text = _clean(_NOTE_MARKS.sub("", "".join(self._text)))
        self._text = []
        if text:
            self.blocks.append((text, self._story_tag is not None))
