import type { ClaimResult, Operation } from "@/lib/api/client";
import { formatAmount, formatPeriod, withUnit } from "@/lib/format";
import { allowedGap, decidingOp } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.chart;

export type ChartSeries = NonNullable<ClaimResult["series"]>;

/** One value of the series, placed in time: 2015 → 2015, 2015-04 → 2015.25. */
export interface ChartPoint {
  period: string;
  value: number;
  time: number;
}

/** A value the claim states ("from 11.9% in 2015"), in the series' unit, with its allowed gap. */
export interface ClaimedMark {
  period: string;
  value: number;
  /** The allowed gap either side; null for a bound ("more than 18%"). */
  gap: number | null;
  holds: boolean;
}

/** Everything the chart draws, from numbers the API computed: none is made here. */
export interface Chart {
  geo: string;
  unit: string | null;
  points: ChartPoint[];
  /** The claim's window as its operation read it; null for a single period. */
  window: { start: string; end: string } | null;
  /** The periods whose values decided the claim (a change's start and end, a level's period). */
  used: string[];
  claimed: ClaimedMark[];
  /** A trend's fitted line over the window: its value at the start and at the end. */
  fit: { start: number; end: number } | null;
}

const PERIOD = /^(\d{4})(?:-(?:(\d{2})|Q([1-4])|S([12])))?$/;

/** Where a period sits in time, in years: the start of its month, quarter or half-year. */
export function periodTime(period: string): number | null {
  const m = PERIOD.exec(period);
  if (!m) return null;
  const [, year, month, quarter, half] = m;
  if (month) return +year + (+month - 1) / 12;
  if (quarter) return +year + (+quarter - 1) / 4;
  if (half) return +year + (+half - 1) / 2;
  return +year;
}

/** The chart for a claim, or null when there is no series to draw. */
export function chartOf(c: ClaimResult): Chart | null {
  const series = c.series;
  if (!series || series.points.length < 2) return null;
  const points: ChartPoint[] = [];
  for (const p of series.points) {
    const time = periodTime(p.period);
    if (time !== null) points.push({ ...p, time });
  }
  if (points.length < 2) return null;
  const known = new Set(points.map((p) => p.period));
  const op = decidingOp(c);
  const own = (op?.inputs ?? []).filter(
    (p) => p.geo === series.geo && known.has(p.period),
  );
  const window = windowOf(op, own, known);
  const claimed = (c.verdict.parts ?? []).flatMap((p) =>
    p.period != null && p.asserted != null && known.has(p.period)
      ? [
          {
            period: p.period,
            value: p.asserted,
            gap: allowedGap(p),
            holds: p.holds,
          },
        ]
      : [],
  );
  const extras = op?.extras ?? {};
  const fit =
    op?.op === "trend" &&
    window &&
    extras.fitted_start != null &&
    extras.fitted_end != null
      ? { start: extras.fitted_start, end: extras.fitted_end }
      : null;
  return {
    geo: series.geo,
    unit: series.unit ?? null,
    points,
    window,
    // A trend reads every value in its window: its fitted line says more than dots would.
    used: op?.op === "trend" ? [] : [...new Set(own.map((p) => p.period))],
    claimed,
    fit,
  };
}

function windowOf(
  op: Operation | undefined,
  own: { period: string }[],
  known: Set<string>,
): Chart["window"] {
  if (!op || !["change", "cagr", "trend"].includes(op.op)) return null;
  if (own.length >= 2) {
    return { start: own[0].period, end: own[own.length - 1].period };
  }
  const start = String(op.args.start ?? "");
  const end = String(op.args.end ?? "");
  return known.has(start) && known.has(end) && start !== end
    ? { start, end }
    : null;
}

/** The line through the points as an SVG path, broken where a period has no value. */
export function linePath(
  points: readonly ChartPoint[],
  step: number,
  x: (time: number) => number,
  y: (value: number) => number,
): string {
  let d = "";
  points.forEach((p, i) => {
    const joined = i > 0 && p.time - points[i - 1].time <= step * 1.5;
    d += `${joined ? "L" : "M"}${x(p.time).toFixed(1)},${y(p.value).toFixed(1)}`;
  });
  return d;
}

/** The span between two periods in years: 1 a year, 1/12 a month. */
export function periodStep(points: readonly ChartPoint[]): number {
  let step = Infinity;
  for (let i = 1; i < points.length; i++) {
    step = Math.min(step, points[i].time - points[i - 1].time);
  }
  return Number.isFinite(step) ? step : 1;
}

/** The lowest and highest value the chart has to show, claimed values and their gaps included. */
export function valueExtent(chart: Chart): [number, number] {
  const values = chart.points.map((p) => p.value);
  for (const m of chart.claimed) {
    values.push(m.value - (m.gap ?? 0), m.value + (m.gap ?? 0));
  }
  if (chart.fit) values.push(chart.fit.start, chart.fit.end);
  return [Math.min(...values), Math.max(...values)];
}

/** The point the chart opens on: the end of the claim's window, else the last value used, else the latest. */
export function initialIndex(chart: Chart): number {
  const at = chart.window?.end ?? chart.used[chart.used.length - 1];
  const i = at ? chart.points.findIndex((p) => p.period === at) : -1;
  return i >= 0 ? i : chart.points.length - 1;
}

/** The point a key moves to, or null for a key the chart does not use. */
export function movePoint(
  index: number,
  key: string,
  count: number,
): number | null {
  switch (key) {
    case "ArrowLeft":
      return Math.max(0, index - 1);
    case "ArrowRight":
      return Math.min(count - 1, index + 1);
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return null;
  }
}

/** The index of the point nearest a time, for a pointer over the chart. */
export function nearestIndex(
  points: readonly ChartPoint[],
  time: number,
): number {
  let best = 0;
  points.forEach((p, i) => {
    if (Math.abs(p.time - time) < Math.abs(points[best].time - time)) best = i;
  });
  return best;
}

/** The series' unit as a sentence names it. */
export function unitText(chart: Chart): string {
  return chart.unit ?? t.noUnit;
}

/** A value with the series' unit: "12.02% of labour force aged 15-74". */
export function valueText(chart: Chart, value: number): string {
  return withUnit(formatAmount(value), chart.unit);
}

function inWindow(chart: Chart, period: string): boolean {
  if (!chart.window) return false;
  const time = periodTime(period) ?? NaN;
  return (
    time >= (periodTime(chart.window.start) ?? Infinity) &&
    time <= (periodTime(chart.window.end) ?? -Infinity)
  );
}

/** What the table and the live line say about one period besides its value. */
export function pointNotes(chart: Chart, period: string): string[] {
  const notes: string[] = [];
  if (chart.window?.start === period) notes.push(t.notes.windowStart);
  else if (chart.window?.end === period) notes.push(t.notes.windowEnd);
  else if (inWindow(chart, period)) notes.push(t.notes.inWindow);
  if (chart.used.includes(period)) notes.push(t.notes.used);
  if (chart.fit && chart.window) {
    if (period === chart.window.start) {
      notes.push(t.notes.fit(valueText(chart, chart.fit.start)));
    } else if (period === chart.window.end) {
      notes.push(t.notes.fit(valueText(chart, chart.fit.end)));
    }
  }
  for (const m of chart.claimed.filter((m) => m.period === period)) {
    notes.push(
      t.notes.claimed(
        valueText(chart, m.value),
        m.gap === null ? null : `±${formatAmount(m.gap)}`,
        m.holds,
      ),
    );
  }
  return notes;
}

/** The live line for the focused point: its period, value and notes. */
export function describePoint(chart: Chart, index: number): string {
  const p = chart.points[index];
  const head = t.point(formatPeriod(p.period), valueText(chart, p.value));
  return [head, ...pointNotes(chart, p.period)].join(" ");
}
