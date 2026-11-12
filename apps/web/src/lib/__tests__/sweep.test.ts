import { describe, expect, it } from "vitest";
import {
  cellState,
  describeCell,
  isNear,
  labelEvery,
  moveCell,
  nearBox,
  ownCell,
  showsLabel,
  subYear,
  sweepSummary,
  windowFigure,
  windowNumber,
  windowUnit,
  type Sweep,
} from "@/lib/sweep";
import { holdingSweep } from "@/test/fixtures";

/** 2013 to 2016, a rise claimed from 2013 to 2016: windows from 2014 do not rise. */
const small: Sweep = {
  op: "change",
  kind: "percent",
  unit: "%",
  starts: ["2013", "2014", "2015", "2016"],
  ends: ["2013", "2014", "2015", "2016"],
  values: [
    [null, 20, 10, 5],
    [null, null, -8, null],
    [null, null, null, 2],
    [null, null, null, null],
  ],
  holds: [
    [null, true, true, true],
    [null, null, false, null],
    [null, null, null, true],
    [null, null, null, null],
  ],
  claim_start: "2013",
  claim_end: "2016",
  near_starts: ["2013", "2014", "2015"],
  near_ends: ["2014", "2015", "2016"],
  counted: 5,
  held: 4,
  share: 0.8,
};

describe("the cherry-pick grid", () => {
  it("tells windows that hold, fail, have no figure, or are not windows", () => {
    expect(cellState(small, { row: 0, col: 1 })).toBe("holds");
    expect(cellState(small, { row: 1, col: 2 })).toBe("fails");
    expect(cellState(small, { row: 1, col: 3 })).toBe("empty");
    expect(cellState(small, { row: 2, col: 1 })).toBe("none");
    expect(cellState(small, { row: 2, col: 2 })).toBe("none");
  });

  it("finds the claim's own window and the nearby block", () => {
    expect(ownCell(small)).toEqual({ row: 0, col: 3 });
    expect(nearBox(small)).toEqual({ top: 0, bottom: 2, left: 1, right: 3 });
    expect(isNear(small, { row: 2, col: 3 })).toBe(true);
    expect(isNear(small, { row: 3, col: 3 })).toBe(false);
    expect(nearBox({ ...small, near_starts: [], near_ends: [] })).toBeNull();
  });

  it("moves with the arrow keys, Home and End, and stops at the edges", () => {
    const at = { row: 1, col: 2 };
    expect(moveCell(small, at, "ArrowUp")).toEqual({ row: 0, col: 2 });
    expect(moveCell(small, at, "ArrowDown")).toEqual({ row: 2, col: 2 });
    expect(moveCell(small, at, "ArrowLeft")).toEqual({ row: 1, col: 1 });
    expect(moveCell(small, at, "ArrowRight")).toEqual({ row: 1, col: 3 });
    expect(moveCell(small, at, "Home")).toEqual({ row: 1, col: 0 });
    expect(moveCell(small, at, "End")).toEqual({ row: 1, col: 3 });
    expect(moveCell(small, { row: 0, col: 0 }, "ArrowUp")).toEqual({
      row: 0,
      col: 0,
    });
    expect(moveCell(small, { row: 3, col: 3 }, "ArrowRight")).toEqual({
      row: 3,
      col: 3,
    });
    expect(moveCell(small, at, "Enter")).toBeNull();
  });
});

describe("what a window says", () => {
  it("writes each kind of figure with its unit", () => {
    expect(windowFigure(small, 20)).toBe("+20%");
    expect(windowFigure(holdingSweep, -4.34)).toBe("-4.34 points");
    expect(windowFigure({ ...small, kind: "ratio" }, 0.5)).toBe("×0.5");
    expect(windowFigure({ ...small, op: "cagr", kind: null }, 2.1)).toBe(
      "+2.1% a year",
    );
    const trend = { ...small, op: "trend", kind: null, unit: "% per year" };
    expect(windowFigure(trend, -0.3)).toBe("-0.3% per year");
    const amount = { ...small, kind: "absolute", unit: "million euro" };
    expect(windowFigure(amount, 1234.567)).toBe("+1,234.57 million euro");
    expect(windowNumber(small, 0)).toBe("0");
  });

  it("names the unit the table is in", () => {
    expect(windowUnit(small)).toBe("per cent change");
    expect(windowUnit(holdingSweep)).toBe("percentage points");
    expect(windowUnit({ ...small, kind: "ratio" })).toMatch(/multiples/);
    expect(windowUnit({ ...small, op: "cagr", kind: null })).toBe(
      "per cent a year",
    );
    expect(windowUnit({ ...small, op: "trend", kind: null, unit: null })).toBe(
      "the series' own unit",
    );
  });

  it("describes a window in words", () => {
    expect(describeCell(small, "up", { row: 0, col: 3 })).toBe(
      "From 2013 to 2016: +5%. The rise shows. This is the claim's own window.",
    );
    expect(describeCell(small, "up", { row: 1, col: 2 })).toBe(
      "From 2014 to 2015: -8%. The rise does not show. A nearby window, so it counts towards the verdict.",
    );
    expect(describeCell(small, "up", { row: 3, col: 3 })).toMatch(
      /not a time window/,
    );
    expect(describeCell(small, "up", { row: 1, col: 3 })).toBe(
      "From 2014 to 2016: the data gives no figure for this window.",
    );
    const far = { ...small, near_starts: ["2013"], near_ends: ["2016"] };
    expect(describeCell(far, "down", { row: 2, col: 3 })).toBe(
      "From 2015 to 2016: +2%. The fall shows.",
    );
    expect(describeCell(far, null, { row: 0, col: 1 })).toBe(
      "From 2013 to 2014: +20%. The claim holds.",
    );
  });

  it("sums up the share, or says why there is none", () => {
    expect(sweepSummary(small, "up", 0.7)).toBe(
      "The rise shows in 4 of the 5 nearby time windows (80%). To hold up, a claim needs at least 70%.",
    );
    expect(sweepSummary(holdingSweep, "down", 0.7)).toBe(
      "The fall shows in all 15 nearby time windows. To hold up, a claim needs at least 70%.",
    );
    expect(sweepSummary(small, "flat", null)).toBe(
      "It stays flat in 4 of the 5 nearby time windows (80%).",
    );
    expect(sweepSummary({ ...small, share: null }, "up", 0.7)).toMatch(
      /too short a span/,
    );
  });
});

describe("axis labels", () => {
  it("labels every year when they fit, else round years plus the claim's own", () => {
    expect(labelEvery(15, 26)).toBe(1);
    expect(labelEvery(50, 26)).toBe(2);
    expect(labelEvery(120, 26)).toBe(5);
    expect(labelEvery(5000, 26)).toBe(50);
    expect(showsLabel("2014", 2, "2015")).toBe(true);
    expect(showsLabel("2015", 2, "2015")).toBe(true);
    expect(showsLabel("2017", 2, "2015")).toBe(false);
  });

  it("knows windows within the year from whole years", () => {
    expect(subYear(small)).toBe(false);
    expect(
      subYear({ ...small, claim_start: "2019-03", claim_end: "2021-09" }),
    ).toBe(true);
  });
});
