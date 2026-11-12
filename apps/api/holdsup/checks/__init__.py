"""Framing checks run after the plan: whether a claim that holds still gives a fair picture.

Modules: `cherry_pick` (the claim's direction over every time window, P3.1), `changepoints`
(breaks in the trend, and a start or end that leans on one, P3.3).
"""

from holdsup.checks.changepoints import ChangePoints, EndpointFlag, change_points, flag_text
from holdsup.checks.cherry_pick import SWEPT_OPS, Sweep, sweep

__all__ = [
    "SWEPT_OPS",
    "ChangePoints",
    "EndpointFlag",
    "Sweep",
    "change_points",
    "flag_text",
    "sweep",
]
