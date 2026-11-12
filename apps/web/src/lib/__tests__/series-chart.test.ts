import { describe, expect, it } from "vitest";
import type { ClaimResult } from "@/lib/api/client";
import {
  chartOf,
  describePoint,
  initialIndex,
  linePath,
  movePoint,
  nearestIndex,
  periodStep,
  periodTime,
  pointNotes,
  unitText,
  valueExtent,
  valueText,
  type ChartPoint,
} from "@/lib/series-chart";
import { strings } from "@/lib/strings";
import { holdingClaim } from "@/test/fixtures";

const t = strings.chart;

const point = (period: string, value: number): ChartPoint => ({
  period,
  value,
  time: periodTime(period)!,
});

// A trend over 2016-2020 as the API answers it (ops/trend.py): the fitted line's ends in extras.
const trendClaim: ClaimResult = {
  ...holdingClaim,
  operations: [
    {
      op: "trend",
      args: { geo: "IT", start: "2016", end: "2020" },
      inputs: ["2016", "2017", "2018", "2019", "2020"].map((period, i) => ({
        geo: "IT",
        period,
        value: [11.72, 11.3, 10.62, 9.91, 9.35][i],
      })),
      value: -0.61,
      extras: { fitted_start: 11.8, fitted_end: 9.36 },
      series: null,
      unit: "percentage points per year",
      flags: [],
    },
  ],
  verdict: { ...holdingClaim.verdict, parts: [] },
};

describe("periodTime", () => {
  it("places years, months, quarters and half-years in years", () => {
    expect(periodTime("2015")).toBe(2015);
    expect(periodTime("2015-04")).toBe(2015.25);
    expect(periodTime("2015-Q3")).toBe(2015.5);
    expect(periodTime("2015-S2")).toBe(2015.5);
    expect(periodTime("latest")).toBeNull();
  });
});

describe("chartOf", () => {
  it("draws a change: its window, the two values it used, the values the claim states", () => {
    const chart = chartOf(holdingClaim)!;
    expect(chart.geo).toBe("IT");
    expect(chart.unit).toBe("% of labour force aged 15-74");
    expect(chart.points).toHaveLength(26);
    expect(chart.points[0]).toEqual({
      period: "2000",
      value: 10.1,
      time: 2000,
    });
    expect(chart.window).toEqual({ start: "2015", end: "2023" });
    expect(chart.used).toEqual(["2015", "2023"]);
    // The assertion part has no period: only the start and end values are marked.
    expect(chart.claimed).toEqual([
      { period: "2015", value: 11.9, gap: 0.169, holds: true },
      { period: "2023", value: 7.7, gap: 0.127, holds: true },
    ]);
    expect(chart.fit).toBeNull();
  });

  it("draws a trend's fitted line instead of dots", () => {
    const chart = chartOf(trendClaim)!;
    expect(chart.window).toEqual({ start: "2016", end: "2020" });
    expect(chart.used).toEqual([]);
    expect(chart.fit).toEqual({ start: 11.8, end: 9.36 });
  });

  it("gives a bound no gap", () => {
    const [start] = holdingClaim.verdict.parts!;
    const chart = chartOf({
      ...holdingClaim,
      verdict: {
        ...holdingClaim.verdict,
        parts: [
          {
            ...start,
            name: "start value",
            period: "2015",
            asserted: 11,
            tolerance: 0.2,
            operator: "more_than",
          },
        ],
      },
    })!;
    expect(chart.claimed).toEqual([
      { period: "2015", value: 11, gap: null, holds: true },
    ]);
  });

  it("has no window for a single period, and only the period it read", () => {
    const chart = chartOf({
      ...holdingClaim,
      operations: [
        {
          ...holdingClaim.operations![0],
          op: "level",
          args: { geo: "IT", period: "2023" },
          inputs: [{ geo: "IT", period: "2023", value: 7.68 }],
        },
      ],
    })!;
    expect(chart.window).toBeNull();
    expect(chart.used).toEqual(["2023"]);
  });

  it("leaves out a peer's values and periods the series does not have", () => {
    const [change] = holdingClaim.operations!;
    const chart = chartOf({
      ...holdingClaim,
      operations: [
        {
          ...change,
          inputs: [
            ...change.inputs,
            { geo: "DE", period: "2015", value: 4.6 },
            { geo: "IT", period: "1990", value: 9 },
          ],
        },
      ],
    })!;
    expect(chart.used).toEqual(["2015", "2023"]);
  });

  it("is null without a series to draw", () => {
    expect(chartOf({ ...holdingClaim, series: null })).toBeNull();
    expect(
      chartOf({
        ...holdingClaim,
        series: {
          ...holdingClaim.series!,
          points: [{ period: "2015", value: 1 }],
        },
      }),
    ).toBeNull();
  });
});

describe("linePath", () => {
  const same = (v: number) => v;
  it("joins neighbouring periods and breaks where one has no value", () => {
    const points = [
      point("2015", 1),
      point("2016", 2),
      point("2018", 3),
      point("2019", 4),
    ];
    expect(linePath(points, periodStep(points), same, same)).toBe(
      "M2015.0,1.0L2016.0,2.0M2018.0,3.0L2019.0,4.0",
    );
  });

  it("reads a month's step from monthly periods", () => {
    const months = [
      point("2020-01", 1),
      point("2020-02", 2),
      point("2020-03", 3),
    ];
    expect(periodStep(months)).toBeCloseTo(1 / 12);
    expect(linePath(months, periodStep(months), same, same)).not.toMatch(
      /M.*M/,
    );
  });
});

describe("valueExtent", () => {
  it("makes room for the claimed values, their gaps and the fitted line", () => {
    const chart = chartOf(holdingClaim)!;
    expect(valueExtent(chart)).toEqual([6.02, 12.78]);
    expect(
      valueExtent({
        ...chart,
        claimed: [{ period: "2015", value: 13, gap: 0.5, holds: false }],
        fit: { start: 5, end: 6 },
      }),
    ).toEqual([5, 13.5]);
  });
});

describe("moving between values", () => {
  const chart = chartOf(holdingClaim)!;

  it("opens on the end of the claim's window", () => {
    expect(chart.points[initialIndex(chart)].period).toBe("2023");
    expect(initialIndex({ ...chart, window: null, used: [] })).toBe(25);
  });

  it("moves with the arrow keys, Home and End, and stops at the ends", () => {
    expect(movePoint(3, "ArrowLeft", 26)).toBe(2);
    expect(movePoint(0, "ArrowLeft", 26)).toBe(0);
    expect(movePoint(25, "ArrowRight", 26)).toBe(25);
    expect(movePoint(3, "Home", 26)).toBe(0);
    expect(movePoint(3, "End", 26)).toBe(25);
    expect(movePoint(3, "ArrowUp", 26)).toBeNull();
  });

  it("finds the value nearest a pointer", () => {
    expect(chart.points[nearestIndex(chart.points, 2015.4)].period).toBe(
      "2015",
    );
    expect(chart.points[nearestIndex(chart.points, 1990)].period).toBe("2000");
  });
});

describe("what a value says", () => {
  const chart = chartOf(holdingClaim)!;

  it("says the unit, or that the series has its own", () => {
    expect(unitText(chart)).toBe("% of labour force aged 15-74");
    expect(unitText({ ...chart, unit: null })).toBe(t.noUnit);
    expect(valueText(chart, 12.02)).toBe("12.02% of labour force aged 15-74");
  });

  it("notes the window, the value used and the claimed value", () => {
    expect(pointNotes(chart, "2015")).toEqual([
      t.notes.windowStart,
      t.notes.used,
      t.notes.claimed("11.9% of labour force aged 15-74", "±0.17", true),
    ]);
    expect(pointNotes(chart, "2019")).toEqual([t.notes.inWindow]);
    expect(pointNotes(chart, "2010")).toEqual([]);
  });

  it("notes a trend's fitted line at the window's ends", () => {
    const trend = chartOf(trendClaim)!;
    expect(pointNotes(trend, "2020")).toEqual([
      t.notes.windowEnd,
      t.notes.fit("9.36% of labour force aged 15-74"),
    ]);
  });

  it("reads a point in words", () => {
    expect(describePoint(chart, 23)).toBe(
      `2023: 7.68% of labour force aged 15-74. ${t.notes.windowEnd} ${t.notes.used} ${t.notes.claimed("7.7% of labour force aged 15-74", "±0.13", true)}`,
    );
  });
});
