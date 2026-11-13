"""The held-out guard: no test-split claim, nor a rewording of one, may reach training.

Every path into training data goes through `check_training_sentences`, which raises with every
problem at once rather than dropping the bad rows quietly: a paraphrase file that names a test
claim is a bug to fix, not noise to filter.
"""

import re
from collections.abc import Iterable, Sequence

from reranker.benchmark import Claim


class LeakageError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__("held-out data would reach training:\n" + "\n".join(self.problems))


def normalize(sentence: str) -> str:
    """Case, spacing and closing punctuation do not make a different sentence."""
    return re.sub(r"\s+", " ", sentence.casefold()).strip().rstrip(".!?").strip()


def held_out_sentences(claims: Iterable[Claim]) -> set[str]:
    """Every held-out quote and text, normalized."""
    out: set[str] = set()
    for c in claims:
        if c.split != "dev":
            out |= {normalize(c.quote), normalize(c.text)}
    return out


def check_training_sentences(sentences: Iterable[tuple[str, str]], claims: Sequence[Claim]) -> None:
    """Raise unless each (claim key, sentence) names a dev claim and the sentence is none of
    the held-out quotes or texts."""
    dev_keys = {c.key for c in claims if c.split == "dev"}
    held_keys = {c.key for c in claims if c.split != "dev"}
    held = held_out_sentences(claims)
    problems: list[str] = []
    for key, sentence in sentences:
        if key in held_keys:
            problems.append(f"{key} is a held-out claim: {sentence!r}")
        elif key not in dev_keys:
            problems.append(f"{key} is not a claim in the benchmark: {sentence!r}")
        if normalize(sentence) in held:
            problems.append(f"{key}: {sentence!r} is a held-out sentence")
    if problems:
        raise LeakageError(problems)
