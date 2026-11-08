"""Deterministic verdict rules and the tolerances they use.

Modules: `model` (Label, Part, Verdict), `tolerances` (what each comparison allows, from
tolerances.yaml), `rules` (deciding one claim and combining several).
"""

from holdsup.verdict.model import Label, Part, Verdict, cant_check
from holdsup.verdict.rules import combine, decide
from holdsup.verdict.tolerances import Tolerances, load_tolerances

__all__ = [
    "Label",
    "Part",
    "Tolerances",
    "Verdict",
    "cant_check",
    "combine",
    "decide",
    "load_tolerances",
]
