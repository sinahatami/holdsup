"""Step 7, the verdict: deterministic rules comparing computed results with the claim.

No model is involved. Every comparison is a `Part` with the computed value, the asserted value
and the tolerance used, so the receipt can show why the label was given.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence

from holdsup.ops import ChangeKind, OpRecord, is_rate, unit_scale
from holdsup.pipeline.claim import AssertionType, ClaimSpec, Direction, Operator
from holdsup.verdict.model import Label, Part, Verdict, cant_check
from holdsup.verdict.tolerances import Tolerances, ValueTolerance

OPERATOR_TEXT = {
    Operator.MORE_THAN: "more than",
    Operator.LESS_THAN: "less than",
    Operator.AT_LEAST: "at least",
    Operator.AT_MOST: "at most",
}


# Claims no operation answers yet: "the lowest since 1977", "met its target", "rose every month".
UNSUPPORTED = frozenset({AssertionType.RECORD, AssertionType.TARGET, AssertionType.STREAK})


class _Rules:
    def __init__(self, claim: ClaimSpec, unit: str | None, tolerances: Tolerances) -> None:
        self.a = claim.assertion
        self.unit = unit
        self.tol = tolerances
        self.rate = is_rate(unit)
        # Asserted amounts in the claim's unit ("billion euros") → the series' ("million euro").
        self.factor = 1.0 if self.rate else unit_scale(self.a.unit) / unit_scale(unit)

    # -- value comparisons --

    def _value_part(
        self,
        name: str,
        computed: float,
        asserted: float,
        tol: ValueTolerance,
        scaled: bool,
        period: str | None = None,
    ) -> Part:
        factor = self.factor if scaled else 1.0
        target, band = asserted * factor, tol.band(asserted) * factor
        # Only the main assertion carries a bound ("fell more than 18%"); stated levels are
        # always "about".
        op = self.a.operator if name == "assertion" else Operator.ABOUT
        holds = self._bounded(op, computed, target, band)
        at = f" for {period}" if period else ""
        claimed = f"{target:.6g} ± {band:.6g}"
        if op is not Operator.ABOUT:
            claimed = f"{OPERATOR_TEXT[op]} {target:.6g} (± {band:.6g})"
        return Part(
            name=name,
            holds=holds,
            computed=computed,
            asserted=target,
            tolerance=band,
            period=period,
            operator=op,
            detail=f"computed {computed:.6g}{at}, asserted {claimed}",
        )

    def _bounded(self, op: Operator, computed: float, target: float, band: float) -> bool:
        """Whether `computed` meets the claim. Bounds compare sizes in the claimed direction:
        "fell more than 18%" holds for a change of -20%."""
        if op is Operator.ABOUT:
            return abs(computed - target) <= band
        flip = target < 0
        c, t = (-computed, -target) if flip else (computed, target)
        if self.a.direction in (Direction.UP, Direction.DOWN) and c < 0:
            return False  # it moved the other way
        if op is Operator.MORE_THAN:
            return c > t
        if op is Operator.LESS_THAN:
            return c < t
        if op is Operator.AT_LEAST:
            return c >= t - band
        return c <= t + band  # at most

    def _signed(self, value: float) -> float:
        return -value if self.a.direction is Direction.DOWN else value

    def _direction_part(self, name: str, delta: float, scale: float, what: str) -> Part:
        """Direction-only check of `delta` (a change, slope or difference); flat means within
        `flat_relative` of `scale`."""
        d = self.a.direction
        if d is Direction.UP:
            holds = delta > 0
        elif d is Direction.DOWN:
            holds = delta < 0
        else:
            holds = abs(delta) <= self.tol.flat_relative * abs(scale)
        return Part(
            name=name, holds=holds, computed=delta, detail=f"{what} {delta:.6g}; claim says {d}"
        )

    def _level_tol(self) -> ValueTolerance:
        return self.tol.values.level_rate if self.rate else self.tol.values.level

    # -- the main assertion, by the operation that answers it --

    def value_at(self, r: OpRecord) -> Part:
        computed = _value(r)
        if self.a.type is AssertionType.LEVEL:
            assert self.a.value is not None  # noqa: S101 (decide: no level claim without a value)
            period = r.inputs[0].period
            return self._value_part(
                "assertion", computed, self.a.value, self._level_tol(), True, period
            )
        # A change claim answered by one value of a growth-rate series ("grew 0.7% in 2024").
        if self.a.value is None:
            return self._direction_part("assertion", computed, 0.0, "growth rate")
        kind = "percentage_points" if self.a.type is AssertionType.PERCENTAGE_POINTS else "percent"
        tol = getattr(self.tol.values, kind)
        return self._value_part("assertion", computed, self._signed(self.a.value), tol, False)

    def change(self, r: OpRecord) -> Part:
        computed = _value(r)
        kind = ChangeKind(str(r.args["kind"]))
        start, end = r.inputs[0].value, r.inputs[1].value
        if self.a.value is None:
            if kind is ChangeKind.RATIO:
                return self._direction_part("assertion", computed - 1, 1.0, "ratio − 1")
            return self._direction_part("assertion", end - start, start, "change")
        tol = getattr(self.tol.values, str(kind))
        if kind is ChangeKind.RATIO:
            return self._value_part("assertion", computed, self.a.value, tol, False)
        asserted = self.a.value if self.a.direction is None else self._signed(self.a.value)
        if self.a.direction is None:  # "changed by 5%": compare sizes only
            computed = abs(computed)
        return self._value_part("assertion", computed, asserted, tol, kind is ChangeKind.ABSOLUTE)

    def cagr(self, r: OpRecord) -> Part:
        computed = _value(r)
        if self.a.value is None:
            return self._direction_part("assertion", computed, 0.0, "yearly growth")
        return self._value_part(
            "assertion", computed, self._signed(self.a.value), self.tol.values.percent, False
        )

    def trend(self, r: OpRecord) -> Part:
        slope = _value(r)
        r2 = r.extras.get("r2")
        start, end = r.extras["fitted_start"], r.extras["fitted_end"]
        if self.a.direction is Direction.FLAT or r2 is None:
            part = self._direction_part("assertion", end - start, start, "fitted change")
            if self.a.direction is not Direction.FLAT:
                part.holds = False  # a constant series neither rises nor falls
            return part
        part = self._direction_part("assertion", slope, 0.0, "slope per year")
        if part.holds and r2 < self.tol.trend_min_r2:
            part.holds = False
            part.detail += f"; R² {r2:.2f} is below {self.tol.trend_min_r2}, so no clear trend"
        return part

    def compare(self, r: OpRecord) -> Part:
        diff = _value(r)
        if self.a.value is None:
            return self._direction_part("assertion", diff, r.inputs[1].value, "difference")
        tol = self.tol.values.percentage_points if self.rate else self.tol.values.absolute
        return self._value_part("assertion", diff, self._signed(self.a.value), tol, True)

    def peers(self, records: Sequence[OpRecord]) -> list[Part]:
        """'Grew more than France and Germany': the claim's place against each peer's change."""
        mine, others = records[0], records[1:]
        parts = []
        for other in others:
            delta = _value(mine) - _value(other)
            part = self._direction_part(
                f"vs {other.args['geo']}", delta, _value(other), "difference in change"
            )
            parts.append(part)
        return parts

    def rank(self, r: OpRecord) -> Part:
        position = _value(r)
        asserted = self.a.value if self.a.value is not None else 1.0
        return self._value_part("assertion", position, asserted, self.tol.values.rank, False)

    # -- "from X to Y" --

    def levels(self, r: OpRecord) -> list[Part]:
        parts = []
        for name, stated, point in (
            ("start value", self.a.start_value, r.inputs[0]),
            ("end value", self.a.end_value, r.inputs[1]),
        ):
            if stated is not None:
                parts.append(
                    self._value_part(
                        name, point.value, stated, self._level_tol(), True, point.period
                    )
                )
        return parts


Judge = Callable[[_Rules, Sequence[OpRecord]], list[Part]]


def _one(rule: Callable[[_Rules, OpRecord], Part]) -> Judge:
    """A judge that checks the first answer record with one rule."""
    return lambda rules, chosen: [rule(rules, chosen[0])]


def _change(rules: _Rules, chosen: Sequence[OpRecord]) -> list[Part]:
    """One change against the claim, or the claim's place against its peers ("grew more than
    France"); then any stated start and end values."""
    first = chosen[0]
    parts = rules.peers(chosen) if len(chosen) > 1 else [rules.change(first)]
    return parts + rules.levels(first)


# How each operation's answer records are judged against the claim. per_capita and deflate make
# series for later calls and never decide a claim themselves (plan validation keeps them out of
# answers).
_JUDGES: Mapping[str, Judge] = {
    "value_at": _one(_Rules.value_at),
    "change": _change,
    "cagr": _one(_Rules.cagr),
    "trend": _one(_Rules.trend),
    "compare": _one(_Rules.compare),
    "rank": _one(_Rules.rank),
}


def _value(r: OpRecord) -> float:
    if r.value is None:
        raise ValueError(f"{r.op} has no value")
    return r.value


def decide(
    claim: ClaimSpec,
    records: Sequence[OpRecord],
    answer: Sequence[int],
    *,
    unit: str | None,
    tolerances: Tolerances,
    window_share: float | None = None,
    distortions: Sequence[str] = (),
) -> Verdict:
    """The verdict for one claim from the records of an executed plan.

    `answer` indexes the records that decide the claim (validated by the planning step);
    `unit` is the series' unit from the catalog.
    """
    a = claim.assertion
    if a.type in UNSUPPORTED:
        return cant_check(f"{a.type} claims cannot be checked yet")
    if a.value is None and a.direction is None and a.type is not AssertionType.RANK:
        return cant_check("the claim states neither a value nor a direction")
    if a.type is AssertionType.LEVEL and a.value is None:
        return cant_check("a level claim without a value")
    chosen = [records[i] for i in answer]
    if not chosen:
        return cant_check("the plan names no result to check")

    judge = _JUDGES.get(chosen[0].op)
    if judge is None:
        return cant_check(f"a {chosen[0].op} result cannot decide a claim")
    parts = judge(_Rules(claim, unit, tolerances), chosen)

    held = [p.holds for p in parts]
    framing = list(distortions)
    if window_share is not None and window_share < tolerances.framing_threshold:
        framing.insert(0, f"holds in {window_share:.0%} of time windows")
    if all(held):
        label = Label.SUPPORTED_FRAMING_MATTERS if framing else Label.SUPPORTED
        reason = "Holds within tolerance" + (f", but {'; '.join(framing)}." if framing else ".")
    elif any(held):
        label, reason = Label.PARTLY_SUPPORTED, _which(parts)
    else:
        label, reason = Label.NOT_SUPPORTED, "Outside tolerance for the stated window."
    return Verdict(
        label=label,
        reason=reason,
        parts=parts,
        window_share=window_share,
        framing_threshold=tolerances.framing_threshold,
        distortions=list(distortions),
        tolerances_version=tolerances.version,
    )


def _which(parts: Iterable[Part]) -> str:
    good = [p.name for p in parts if p.holds]
    bad = [p.name for p in parts if not p.holds]
    return f"Holds for {', '.join(good)}; not for {', '.join(bad)}."


def combine(labels: Sequence[Label]) -> Label:
    """One label for a text with several claims."""
    checked = [label for label in labels if label is not Label.CANT_CHECK]
    if not checked:
        return Label.CANT_CHECK
    if len(set(checked)) == 1:
        return checked[0]
    if set(checked) == {Label.SUPPORTED, Label.SUPPORTED_FRAMING_MATTERS}:
        return Label.SUPPORTED_FRAMING_MATTERS  # every claim holds; some framing caveats
    return Label.PARTLY_SUPPORTED
