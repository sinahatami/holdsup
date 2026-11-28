"""Every sentence the Telegram bot says (HTML, Telegram's subset). Verdict names mirror the
site's (apps/web/src/lib/strings/index.ts, `verdicts`)."""

from holdsup.verdict import Label

LABELS = {
    Label.SUPPORTED: "Holds up",
    Label.SUPPORTED_FRAMING_MATTERS: "Holds up, but the framing matters",
    Label.NOT_SUPPORTED: "Does not hold up",
    Label.PARTLY_SUPPORTED: "Partly holds up",
    Label.CANT_CHECK: "Can't check",
}

EXAMPLE = "Italy's unemployment rate fell to 7.7% in 2023."

START = (
    "<b>HoldsUp</b> checks the numbers in what people say against official statistics "
    "(Eurostat, the World Bank, Our World in Data), with the arithmetic done in code.\n\n"
    "Send me a sentence with a figure, for example:\n<i>{example}</i>\n\n"
    "or a link to an article. I answer with a verdict per claim and a receipt that shows "
    "every step.\n\n"
    'Every check is kept, and anyone with its link can open it. <a href="{site}/privacy">'
    "Privacy</a>"
)
HELP = (
    "Send me a sentence with a figure, or a link to an article, and I check it against "
    "official statistics. For example:\n<i>{example}</i>\n\n"
    '<a href="{site}/methodology">How it works</a> · <a href="{site}/privacy">Privacy</a>'
)
NOT_TEXT = "Send me text with a figure in it, or a link to an article."
TOO_LONG = (
    "That is longer than {limit} characters. Send the sentence with the figure, or a link "
    "to the article."
)
CHECKING = "Checking against the official figures…"
NO_CLAIMS = "I found no claim with a number in it. Try a sentence such as “{example}”"
FROM_PAGE = 'From <a href="{url}">{title}</a>'
SOURCE = "<i>{indicator} · {source}</i>"
RECEIPT = '<a href="{url}">See the receipt</a>'
MORE_CLAIMS = "…and {n} more in the receipt."
TOO_MANY_CHECKS = (
    "You have started too many new checks this hour. Try again in about {minutes}. Claims "
    "that were checked before still answer straight away."
)
TOO_MANY_LINKS = (
    "You have sent too many links this hour. Try again in about {minutes}, or paste the "
    "sentence instead."
)
FAILED = "Sorry, that check failed. Please try again later."


def minutes(seconds: int | None) -> str:
    """'1 minute', '25 minutes': a wait rounded up to whole minutes."""
    m = max(1, -(-(seconds or 60) // 60))
    return "1 minute" if m == 1 else f"{m} minutes"
