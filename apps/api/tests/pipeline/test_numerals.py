import pytest

from holdsup.pipeline.numerals import written_half_unit


@pytest.mark.parametrize(
    ("text", "stated", "scale", "half"),
    [
        ("fell from 60.3 million to 58.0 million", 58.0, 1e6, 0.05),  # a trailing zero counts
        ("fell from 60.3 million to 58 million", 58.0, 1e6, 0.5),
        ("it was 3.0% in 2019", 3.0, 1.0, 0.05),
        ("it was 26% in 2013", 26.0, 1.0, 0.5),
        ("it was 28,000 euros", 28.0, 1e3, 0.5),  # a rounded figure, to the thousand
        ("debt of 1.66 million euros", 1.66, 1e6, 0.005),
        ("it fell by -4.3%", -4.3, 1.0, 0.05),  # a stated change carries its sign
    ],
)
def test_half_a_unit_of_the_last_digit_as_written(
    text: str, stated: float, scale: float, half: float
) -> None:
    assert written_half_unit(text, stated, scale) == pytest.approx(half)


def test_a_number_the_text_does_not_write_has_no_written_precision() -> None:
    assert written_half_unit("it more than doubled", 2.0) is None
    assert written_half_unit("it was 26% in 2013", 27.0) is None
    assert written_half_unit("58 million", 58.0, 1.0) is None  # wrong scale: 58e6, not 58
