"""Safe analysis operations: pure, typed, no I/O. The only place numbers users see are computed."""

from holdsup.ops.change import ChangeKind, change

__all__ = ["ChangeKind", "change"]
