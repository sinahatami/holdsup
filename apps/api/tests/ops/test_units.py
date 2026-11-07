import pytest

from holdsup.ops import is_rate, unit_scale


@pytest.mark.parametrize(
    ("unit", "scale"),
    [
        ("million euro (current prices)", 1e6),
        ("billion euros", 1e9),
        ("Thousand persons", 1e3),
        ("trillion", 1e12),
        ("MIO_EUR", 1e6),
        ("euro per person", 1.0),
        ("", 1.0),
        (None, 1.0),
    ],
)
def test_unit_scale(unit: str | None, scale: float) -> None:
    assert unit_scale(unit) == scale


def test_is_rate() -> None:
    assert is_rate("% of GDP") and is_rate(" %")
    assert not is_rate("million euro") and not is_rate(None) and not is_rate("")
