"""Framing checks run after the plan: whether a claim that holds still gives a fair picture.

Modules: `cherry_pick` (the claim's direction over every time window, P3.1).
"""

from holdsup.checks.cherry_pick import SWEPT_OPS, Sweep, sweep

__all__ = ["SWEPT_OPS", "Sweep", "sweep"]
