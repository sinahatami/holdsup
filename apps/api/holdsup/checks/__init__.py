"""Framing checks run after the plan: whether a claim that holds still gives a fair picture.

Modules: `cherry_pick` (the claim's direction over every time window, P3.1), `changepoints`
(breaks in the trend, and a start or end that leans on one, P3.3), `distortions` (per person,
after inflation, percent or points, definition, stale data, and the start and end, P3.4).
"""

from holdsup.checks.changepoints import ChangePoints, EndpointFlag, change_points, flag_text
from holdsup.checks.cherry_pick import SWEPT_OPS, Sweep, sweep
from holdsup.checks.distortions import (
    CheckInput,
    CheckKind,
    DistortionCheck,
    Related,
    distortion_checks,
    said_between,
    wants_real_terms,
)

__all__ = [
    "SWEPT_OPS",
    "ChangePoints",
    "CheckInput",
    "CheckKind",
    "DistortionCheck",
    "EndpointFlag",
    "Related",
    "Sweep",
    "change_points",
    "distortion_checks",
    "flag_text",
    "said_between",
    "sweep",
    "wants_real_terms",
]
