"""The confidence model's signals, scoring, cut-offs and reasons (P4.5)."""

import math
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from holdsup.ml.confidence import (
    FEATURES,
    GENERIC_REASON,
    MAX_BOUNDARY_DISTANCE,
    NOT_CONFIDENT,
    ConfidenceModel,
    Signals,
    boundary_distance,
    data_age_years,
    load_confidence,
    rerank_signals,
    unscored,
    vector,
)
from holdsup.pipeline.claim import Operator
from holdsup.verdict.model import Part

TRAINED_ON = {
    "created": "2026-11-14",
    "eval_version": "1.0.0",
    "catalog_version": "0.1.0",
    "reports": {"dev.json": "0" * 64},
    "rows": 90,
    "seed": 13,
}


def model(**over: Any) -> ConfidenceModel:  # Any: field values of several types
    """Standardization as the identity, so a coefficient reads straight off the raw value."""
    n = len(FEATURES)
    fields: dict[str, Any] = {  # Any: as above
        "features": list(FEATURES),
        "impute": [0.0] * n,
        "center": [0.0] * n,
        "scale": [1.0] * n,
        "coef": [0.0] * n,
        "intercept": 0.0,
        "threshold": 0.6,
        "high": 0.85,
        "target_accuracy": 0.9,
        "trained_on": TRAINED_ON,
    }
    fields.update(over)
    return ConfidenceModel.model_validate(fields)


def coef(**weights: float) -> list[float]:
    return [weights.get(name, 0.0) for name in FEATURES]


# --- signals ---------------------------------------------------------------------------------


def test_the_matched_statistic_s_probability_and_margin() -> None:
    candidates = [("a", 0.9), ("b", 0.3), ("c", 0.1)]
    assert rerank_signals(candidates, "a") == (0.9, 0.6)
    # The model picked the reranker's second: its margin is below zero.
    assert rerank_signals(candidates, "b") == (0.3, -0.6)


def test_a_lone_candidate_s_margin_is_its_probability() -> None:
    assert rerank_signals([("a", 0.7)], "a") == (0.7, 0.7)


def test_no_reranker_score_means_no_signal() -> None:
    assert rerank_signals([("a", None), ("b", None)], "a") == (None, None)
    assert rerank_signals([("a", 0.9)], "z") == (None, None)


def test_data_age_counts_from_the_end_of_the_period() -> None:
    assert data_age_years("2024", date(2026, 11, 13)) == pytest.approx(23 / 12, abs=0.01)
    assert data_age_years("2026-09", date(2026, 11, 13)) == pytest.approx(2 / 12, abs=0.01)
    assert data_age_years(None, date(2026, 11, 13)) is None
    assert data_age_years("not a period", date(2026, 11, 13)) is None


def part(
    computed: float | None,
    asserted: float | None,
    tolerance: float | None,
    op: Operator = Operator.ABOUT,
) -> Part:
    return Part(
        name="assertion",
        holds=True,
        computed=computed,
        asserted=asserted,
        tolerance=tolerance,
        operator=op,
        detail="",
    )


@pytest.mark.parametrize(
    ("p", "distance"),
    [
        (part(-4.2, -4.0, 0.5), 0.6),  # 0.2 off, 0.3 inside the band of 0.5
        (part(10.0, 10.0, 2.0), 1.0),  # dead on: a whole band from either edge
        (part(13.0, 10.0, 2.0), 0.5),  # outside, half a band past the edge
        (part(100.0, 10.0, 2.0), MAX_BOUNDARY_DISTANCE),  # far out: capped
        (part(21.0, 18.0, 1.0, Operator.MORE_THAN), 3.0),
        (part(-21.0, -18.0, 1.0, Operator.MORE_THAN), 3.0),  # "fell more than 18%"
        (part(17.0, 18.0, 1.0, Operator.LESS_THAN), 1.0),
        (part(17.5, 18.0, 1.0, Operator.AT_LEAST), 0.5),  # the edge is 17
        (part(19.5, 18.0, 1.0, Operator.AT_MOST), 0.5),  # the edge is 19
    ],
)
def test_distance_from_the_tolerance_s_edge(p: Part, distance: float) -> None:
    assert boundary_distance([p]) == pytest.approx(distance)


def test_the_closest_part_decides_and_parts_without_a_band_are_skipped() -> None:
    parts = [
        part(10.0, 10.0, 2.0),
        part(12.5, 10.0, 2.0),  # 0.25
        part(1.0, None, None),  # a direction-only part
        part(3.0, 3.0, 0.0),  # a rank: no band
    ]
    assert boundary_distance(parts) == pytest.approx(0.25)
    assert boundary_distance([part(-1.0, None, None)]) is None
    assert boundary_distance([]) is None


def test_the_model_reads_the_length_on_a_log_scale_and_no_negative_age() -> None:
    s = Signals(
        rerank_probability=0.9,
        rerank_margin=0.5,
        definition_mismatch=True,
        data_age_years=-0.5,
        series_length=9,
        boundary_distance=1.5,
        fallback_steps=2,
    )
    assert vector(s) == [0.9, 0.5, 1.0, 0.0, pytest.approx(math.log(10)), 1.5, 2.0]
    assert vector(Signals()) == [None, None, 0.0, None, None, None, 0.0]


# --- the model -------------------------------------------------------------------------------


def test_the_probability_is_the_logistic_of_the_standardized_signals() -> None:
    m = model(
        coef=coef(rerank_margin=2.0, fallback_steps=-1.0),
        center=[0.0, 0.5, 0, 0, 0, 0, 0],
        scale=[1.0, 0.25, 1, 1, 1, 1, 1],
        intercept=0.5,
    )
    s = Signals(rerank_margin=0.75, fallback_steps=1)
    logit = 0.5 + 2.0 * (0.75 - 0.5) / 0.25 - 1.0 * 1
    assert m.probability(s) == pytest.approx(1 / (1 + math.exp(-logit)))


def test_a_missing_signal_reads_as_the_training_mean() -> None:
    m = model(
        coef=coef(rerank_probability=3.0),
        impute=[0.8, 0, 0, 0, 0, 0, 0],
        center=[0.8, 0, 0, 0, 0, 0, 0],
    )
    assert m.contributions(Signals())[0] == 0.0
    assert m.probability(Signals()) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("intercept", "label", "abstain"),
    [(3.0, "high", False), (0.8, "medium", False), (-1.0, "low", True)],
)
def test_the_cut_offs_set_the_label(intercept: float, label: str, abstain: bool) -> None:
    c = model(intercept=intercept).score(Signals())
    assert (c.label, c.abstain) == (label, abstain)
    assert c.probability == pytest.approx(1 / (1 + math.exp(-intercept)), abs=1e-4)
    assert (c.reason is None) is not abstain
    assert c.model == "logistic regression (trained 2026-11-14)"


def test_an_abstention_names_the_two_signals_that_pulled_hardest() -> None:
    m = model(
        coef=coef(
            rerank_margin=2.0, definition_mismatch=-1.0, boundary_distance=1.0, fallback_steps=-3.0
        ),
        center=[0, 0.4, 0, 0, 0, 1.0, 0],
    )
    s = Signals(
        rerank_margin=0.1, definition_mismatch=True, boundary_distance=0.2, fallback_steps=1
    )
    c = m.score(s)
    assert c.abstain
    # Pulls: fallback -3, definition -1, boundary -0.8, margin -0.6: the first two are named.
    assert c.reason == (
        f"{NOT_CONFIDENT} a backup model did part of the work, and what the claim describes "
        "differs from the statistic's definition."
    )


def test_a_signal_whose_weight_points_the_unexpected_way_gives_no_reason() -> None:
    # Older data scored as more likely right: a quirk of the training data, never a reason.
    m = model(coef=coef(data_age_years=1.0, series_length=1.0), center=[0, 0, 0, 5.0, 3.0, 0, 0])
    s = Signals(data_age_years=1.0, series_length=4)  # log1p(4) < 3: a short series
    assert m.reason(s) == f"{NOT_CONFIDENT} the series has only 4 values."


def test_no_signal_on_its_worse_side_gives_the_general_reason() -> None:
    m = model(coef=coef(rerank_margin=2.0), center=[0, 0.2, 0, 0, 0, 0, 0], intercept=-5.0)
    c = m.score(Signals(rerank_margin=0.9))
    assert c.abstain and c.reason == f"{NOT_CONFIDENT} {GENERIC_REASON}"


@pytest.mark.parametrize(
    ("age", "words"), [(0.4, "less than a year"), (1.2, "about 1 year"), (3.6, "about 4 years")]
)
def test_old_data_is_named_in_years(age: float, words: str) -> None:
    m = model(coef=coef(data_age_years=-1.0), center=[0, 0, 0, 0.1, 0, 0, 0])
    assert m.reason(Signals(data_age_years=age)) == (
        f"{NOT_CONFIDENT} the newest figure it could use is {words} old."
    )


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("rerank_probability", "the statistic it matched is not a clear fit"),
        ("boundary_distance", "close to the edge of the tolerance"),
    ],
)
def test_each_signal_has_its_own_words(name: str, text: str) -> None:
    i = FEATURES.index(name)
    center = [0.0] * len(FEATURES)
    center[i] = 1.0
    m = model(coef=coef(**{name: 1.0}), center=center)
    assert text in m.reason(Signals(**{name: 0.2}))


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"features": list(reversed(FEATURES))}, "are not"),
        ({"coef": [0.0]}, "coef needs 7 values"),
        ({"scale": [1, 1, 1, 0, 1, 1, 1]}, "every scale must be positive"),
        ({"threshold": 0.9, "high": 0.8}, "cannot be below"),
        ({"surprise": 1}, "Extra inputs"),
    ],
)
def test_a_model_file_that_does_not_fit_is_refused(over: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        model(**over)


def test_without_a_model_a_claim_carries_its_signals_only() -> None:
    c = unscored(Signals(fallback_steps=1))
    assert c.signals.fallback_steps == 1
    assert (c.probability, c.label, c.abstain, c.reason, c.model) == (None, None, False, None, None)


def test_loading(tmp_path: Path) -> None:
    assert load_confidence(tmp_path / "absent.json") is None
    path = tmp_path / "model.json"
    path.write_text(model(intercept=1.0).model_dump_json(), encoding="utf-8")
    loaded = load_confidence(path)
    assert loaded is not None and loaded.intercept == 1.0


def test_wiring_runs_without_a_model_and_says_so(tmp_path: Path) -> None:
    from structlog.testing import capture_logs

    from holdsup.service.wiring import optional_confidence

    with capture_logs() as logs:
        assert optional_confidence(tmp_path / "absent.json") is None
    assert [e["event"] for e in logs] == ["confidence_model_missing"]
    path = tmp_path / "model.json"
    path.write_text(model().model_dump_json(), encoding="utf-8")
    assert optional_confidence(path) is not None


def test_the_committed_model_loads_and_reads_these_signals() -> None:
    from holdsup.ml.confidence import MODEL_FILE

    if not MODEL_FILE.exists():
        pytest.skip("no model trained yet (make eval, then make confidence-train)")
    loaded = load_confidence()
    assert loaded is not None and tuple(loaded.features) == FEATURES
    assert 0 <= loaded.threshold <= loaded.high <= 1
