import type { ClaimResult } from "@/lib/api/client";
import { formatPeriod, withUnit } from "@/lib/format";
import { strings } from "@/lib/strings";

/** The claim's direction over every time window, as the API's cherry-pick sweep returns it. */
export type Sweep = NonNullable<ClaimResult["sweep"]>;
export type Direction = NonNullable<
  ClaimResult["claim"]["assertion"]["direction"]
>;

/** A cell of the grid: a row (start period) and a column (end period). */
export interface Cell {
  row: number;
  col: number;
}

/**
 * What a cell shows: the claim's direction holds there or not, a window with no figure
 * (a missing value, a percent change from 0), or no window at all (the end is not after the
 * start). Periods within one sweep share a format, so they compare as text.
 */
export type CellState = "holds" | "fails" | "empty" | "none";

export function cellState(s: Sweep, { row, col }: Cell): CellState {
  const holds = s.holds[row]?.[col];
  if (holds === true) return "holds";
  if (holds === false) return "fails";
  return s.starts[row] < s.ends[col] ? "empty" : "none";
}

/** The claim's own window. */
export function ownCell(s: Sweep): Cell {
  return {
    row: s.starts.indexOf(s.claim_start),
    col: s.ends.indexOf(s.claim_end),
  };
}

export function isOwn(s: Sweep, { row, col }: Cell): boolean {
  return s.starts[row] === s.claim_start && s.ends[col] === s.claim_end;
}

/** Whether a window is one of the nearby ones the verdict's share counts. */
export function isNear(s: Sweep, { row, col }: Cell): boolean {
  return (
    s.near_starts.includes(s.starts[row]) && s.near_ends.includes(s.ends[col])
  );
}

/** The block of nearby windows (first and last row and column), or null when none count. */
export function nearBox(
  s: Sweep,
): { top: number; bottom: number; left: number; right: number } | null {
  if (s.near_starts.length === 0 || s.near_ends.length === 0) return null;
  return {
    top: s.starts.indexOf(s.near_starts[0]),
    bottom: s.starts.indexOf(s.near_starts[s.near_starts.length - 1]),
    left: s.ends.indexOf(s.near_ends[0]),
    right: s.ends.indexOf(s.near_ends[s.near_ends.length - 1]),
  };
}

/** Where a key moves the focused cell: arrows by one, Home and End to the row's ends. */
export function moveCell(s: Sweep, at: Cell, key: string): Cell | null {
  const lastRow = s.starts.length - 1;
  const lastCol = s.ends.length - 1;
  switch (key) {
    case "ArrowUp":
      return { ...at, row: Math.max(0, at.row - 1) };
    case "ArrowDown":
      return { ...at, row: Math.min(lastRow, at.row + 1) };
    case "ArrowLeft":
      return { ...at, col: Math.max(0, at.col - 1) };
    case "ArrowRight":
      return { ...at, col: Math.min(lastCol, at.col + 1) };
    case "Home":
      return { ...at, col: 0 };
    case "End":
      return { ...at, col: lastCol };
    default:
      return null;
  }
}

const signed = new Intl.NumberFormat(strings.locale, {
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const plain = new Intl.NumberFormat(strings.locale, {
  maximumFractionDigits: 2,
});

/** A window's figure on its own, as the table shows it: "+20", "-4.34", "×0.5". */
export function windowNumber(s: Sweep, value: number): string {
  return s.kind === "ratio" ? `×${plain.format(value)}` : signed.format(value);
}

/** A window's figure with its unit: "-4.34 points", "+20%", "×0.5", "+2.1% a year". */
export function windowFigure(s: Sweep, value: number): string {
  const n = windowNumber(s, value);
  if (s.kind === "ratio") return n;
  if (s.kind === "percent") return `${n}%`;
  if (s.kind === "percentage_points") return strings.windows.points(n);
  if (s.op === "cagr") return strings.windows.perYear(n);
  return withUnit(n, s.unit);
}

/** The unit every figure in the table is in, for its caption. */
export function windowUnit(s: Sweep): string {
  if (s.kind === "ratio") return strings.windows.units.ratio;
  if (s.kind === "percent") return strings.windows.units.percent;
  if (s.kind === "percentage_points") return strings.windows.units.points;
  if (s.op === "cagr") return strings.windows.units.cagr;
  return s.unit ?? strings.windows.units.none;
}

/** What one cell says, for the line under the chart and for a screen reader. */
export function describeCell(
  s: Sweep,
  direction: Direction | null,
  at: Cell,
): string {
  const t = strings.windows;
  const start = formatPeriod(s.starts[at.row]);
  const end = formatPeriod(s.ends[at.col]);
  const state = cellState(s, at);
  if (state === "none") return t.notAWindow(start, end);
  if (state === "empty") return t.noFigure(start, end);
  const value = s.values[at.row][at.col] as number;
  const how = state === "holds" ? t.shows : t.showsNot;
  const text = t.cell(
    start,
    end,
    windowFigure(s, value),
    how[direction ?? "none"],
  );
  if (isOwn(s, at)) return `${text} ${t.ownWindow}`;
  return isNear(s, at) ? `${text} ${t.nearWindow}` : text;
}

/** The verdict's share in a sentence, or why there is none. */
export function sweepSummary(
  s: Sweep,
  direction: Direction | null,
  threshold: number | null | undefined,
): string {
  const t = strings.windows;
  if (s.share === null || s.share === undefined) return t.noShare;
  const pct = Math.round(s.share * 100);
  const need =
    threshold === null || threshold === undefined
      ? null
      : Math.round(threshold * 100);
  return t.summary(t.shows[direction ?? "none"], s.held, s.counted, pct, need);
}

/**
 * Which axis labels to print: every year when they fit, else round years (every 2, 5, 10 or
 * 20), so that labels never crowd. The claim's own start and end are always printed.
 */
export function labelEvery(count: number, room: number): number {
  return [1, 2, 5, 10, 20].find((k) => count / k <= room) ?? 50;
}

export function showsLabel(
  period: string,
  every: number,
  own: string,
): boolean {
  return period === own || Number(period.slice(0, 4)) % every === 0;
}

/** True when windows are within the year (months, quarters, half-years), not whole years. */
export function subYear(s: Sweep): boolean {
  return s.claim_start.length > 4;
}
