from collections.abc import Iterator

import pytest

from holdsup.config import get_settings
from holdsup.db.session import get_engine, get_sessionmaker


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    """Settings and engines are cached; reset them around every test."""
    for cached in (get_settings, get_engine, get_sessionmaker):
        cached.cache_clear()
    yield
    for cached in (get_settings, get_engine, get_sessionmaker):
        cached.cache_clear()
