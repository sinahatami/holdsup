"""Where checks live: in memory (tests, local runs) or in Postgres.

Modules: `model` (the stored shapes and the `CheckStore` protocol), `memory` and `sql` (one
implementation each). Callers depend on `CheckStore`; the wiring picks the implementation.
"""

from holdsup.service.store.memory import InMemoryCheckStore
from holdsup.service.store.model import (
    CheckResult,
    CheckStatus,
    CheckStore,
    ReportKind,
    StoredCheck,
    StoredReport,
    add_entry,
)
from holdsup.service.store.sql import SqlCheckStore

__all__ = [
    "CheckResult",
    "CheckStatus",
    "CheckStore",
    "InMemoryCheckStore",
    "ReportKind",
    "SqlCheckStore",
    "StoredCheck",
    "StoredReport",
    "add_entry",
]
