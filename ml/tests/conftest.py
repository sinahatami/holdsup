"""Fixtures over tests/helpers.py."""

from functools import cache

import pytest

from holdsup.catalog.schema import Catalog
from reranker.benchmark import Claim
from tests import helpers

_catalog = cache(helpers.catalog)


@pytest.fixture
def claims() -> list[Claim]:
    return helpers.claims()


@pytest.fixture
def catalog() -> Catalog:
    return _catalog()
