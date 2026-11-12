"use client";

import { scaleBand } from "d3-scale";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { formatPeriod } from "@/lib/format";
import { strings } from "@/lib/strings";
import {
  cellState,
  describeCell,
  isNear,
  isOwn,
  labelEvery,
  moveCell,
  nearBox,
  ownCell,
  showsLabel,
  subYear,
  sweepSummary,
  windowNumber,
  windowUnit,
  type Cell,
  type CellState,
  type Direction,
  type Sweep,
} from "@/lib/sweep";

const t = strings.windows;

// The chart's own units: one window, the room for start years (left) and end years (top).
const CELL = 12;
const LEFT = 34;
const TOP = 30;
// At most this many years are labelled on an axis; the claim's own are always labelled.
const LABELS = 26;

const FILL: Record<Exclude<CellState, "none">, string> = {
  holds: "fill-(--sweep-holds)",
  fails: "", // the hatch pattern
  empty: "fill-(--sweep-empty)",
};

const HATCH: CSSProperties = {
  background:
    "repeating-linear-gradient(45deg, var(--sweep-fails) 0 2px, var(--sweep-hatch) 2px 3px)",
};

/**
 * The cherry-pick heatmap: every start year (rows) by every end year (columns), each window
 * coloured by whether the claim's direction holds there. The claim's own window is outlined
 * and the nearby windows the verdict counts are boxed. The picture is for the eye; the
 * focusable frame takes the arrow keys and says each window in words, and the table holds
 * every figure.
 */
export function WindowHeatmap({
  sweep,
  direction,
  threshold,
}: {
  sweep: Sweep;
  direction: Direction | null;
  /** The verdict's framing threshold (a share), for the summary. */
  threshold: number | null | undefined;
}) {
  const id = useId().replace(/[^\w-]/g, "");
  const ids = {
    heading: `${id}-heading`,
    readout: `${id}-readout`,
    keys: `${id}-keys`,
    table: `${id}-table`,
    hatch: `${id}-hatch`,
  };
  const own = ownCell(sweep);
  const [active, setActive] = useState<Cell>(
    own.row >= 0 && own.col >= 0 ? own : { row: 0, col: 0 },
  );
  const [focused, setFocused] = useState(false);
  const [pointing, setPointing] = useState(false);
  const [table, setTable] = useState(false);
  const frame = useRef<HTMLDivElement>(null);

  const x = scaleBand<string>()
    .domain(sweep.ends)
    .range([LEFT, LEFT + sweep.ends.length * CELL])
    .paddingInner(0.1);
  const y = scaleBand<string>()
    .domain(sweep.starts)
    .range([TOP, TOP + sweep.starts.length * CELL])
    .paddingInner(0.1);
  const width = LEFT + sweep.ends.length * CELL + 2;
  const height = TOP + sweep.starts.length * CELL + 2;
  const box = (c: Cell, inset = 0) => ({
    x: (x(sweep.ends[c.col]) ?? 0) + inset,
    y: (y(sweep.starts[c.row]) ?? 0) + inset,
    width: x.bandwidth() - 2 * inset,
    height: y.bandwidth() - 2 * inset,
  });
  const near = nearBox(sweep);
  const everyCol = labelEvery(sweep.ends.length, LABELS);
  const everyRow = labelEvery(sweep.starts.length, LABELS);

  // A long grid scrolls inside its frame on a narrow screen: start with the claim's window
  // in view rather than the oldest years.
  const ownX = own.col >= 0 ? (x(sweep.ends[own.col]) ?? 0) : 0;
  useEffect(() => {
    const el = frame.current;
    if (!el || el.scrollWidth <= el.clientWidth) return;
    const scale = el.scrollWidth / width;
    el.scrollLeft = ownX * scale - el.clientWidth / 2;
  }, [ownX, width]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const next = moveCell(sweep, active, e.key);
    if (next === null) return;
    e.preventDefault();
    setActive(next);
  };
  const pick = (e: PointerEvent<SVGGElement>) => {
    const target = e.target as Element;
    const row = target.getAttribute("data-row");
    const col = target.getAttribute("data-col");
    if (row !== null && col !== null) setActive({ row: +row, col: +col });
  };

  return (
    <section aria-labelledby={ids.heading} className="flex flex-col gap-3">
      <Eyebrow as="h3" id={ids.heading}>
        {t.heading}
      </Eyebrow>
      <p className="leading-7">{sweepSummary(sweep, direction, threshold)}</p>
      <p className="text-muted-foreground text-sm leading-6">
        {t.howToRead}
        {subYear(sweep) &&
          ` ${t.subYear(formatPeriod(sweep.claim_start), formatPeriod(sweep.claim_end))}`}
      </p>

      <div
        ref={frame}
        role="group"
        dir="ltr" // years run left to right in any language
        tabIndex={0}
        aria-label={t.chartLabel}
        aria-describedby={`${ids.keys} ${ids.readout}`}
        onKeyDown={onKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        // Its width comes from the card, never from the chart: a long grid scrolls inside.
        className="focus-visible:ring-brand overflow-x-auto rounded-lg outline-none [contain:inline-size] focus-visible:ring-2"
      >
        <svg
          aria-hidden
          viewBox={`0 0 ${width} ${height}`}
          className="block"
          style={{ width: "100%", minWidth: width * 0.75, maxWidth: width * 2 }}
          data-testid="window-heatmap"
        >
          <defs>
            <pattern
              id={ids.hatch}
              width="3"
              height="3"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <rect width="3" height="3" className="fill-(--sweep-fails)" />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="3"
                strokeWidth="1.2"
                className="stroke-(--sweep-hatch)"
              />
            </pattern>
          </defs>
          <text x={2} y={TOP - 4} className="fill-muted-foreground text-[8px]">
            {t.start} ↓
          </text>
          <text x={LEFT} y={8} className="fill-muted-foreground text-[8px]">
            {t.end} →
          </text>
          {sweep.ends.map(
            (end) =>
              showsLabel(end, everyCol, sweep.claim_end) && (
                <text
                  key={end}
                  transform={`translate(${(x(end) ?? 0) + x.bandwidth() / 2 + 3}, ${TOP - 3}) rotate(-90)`}
                  className={label(end === sweep.claim_end)}
                >
                  {end.slice(0, 4)}
                </text>
              ),
          )}
          {sweep.starts.map(
            (start) =>
              showsLabel(start, everyRow, sweep.claim_start) && (
                <text
                  key={start}
                  x={LEFT - 3}
                  y={(y(start) ?? 0) + y.bandwidth() / 2 + 3}
                  textAnchor="end"
                  className={label(start === sweep.claim_start)}
                >
                  {start.slice(0, 4)}
                </text>
              ),
          )}
          <g
            onPointerOver={pick}
            onPointerDown={pick}
            onPointerEnter={() => setPointing(true)}
            onPointerLeave={() => setPointing(false)}
          >
            {sweep.starts.map((_, row) =>
              sweep.ends.map((_, col) => {
                const state = cellState(sweep, { row, col });
                if (state === "none") return null;
                return (
                  <rect
                    key={`${row}-${col}`}
                    data-row={row}
                    data-col={col}
                    data-state={state}
                    data-own={isOwn(sweep, { row, col }) || undefined}
                    data-near={isNear(sweep, { row, col }) || undefined}
                    {...box({ row, col })}
                    className={FILL[state]}
                    fill={state === "fails" ? `url(#${ids.hatch})` : undefined}
                  />
                );
              }),
            )}
          </g>
          {near && (
            <rect
              x={(x(sweep.ends[near.left]) ?? 0) - 1.5}
              y={(y(sweep.starts[near.top]) ?? 0) - 1.5}
              width={
                (x(sweep.ends[near.right]) ?? 0) -
                (x(sweep.ends[near.left]) ?? 0) +
                x.bandwidth() +
                3
              }
              height={
                (y(sweep.starts[near.bottom]) ?? 0) -
                (y(sweep.starts[near.top]) ?? 0) +
                y.bandwidth() +
                3
              }
              fill="none"
              strokeWidth="1"
              strokeDasharray="3 2"
              className="stroke-foreground pointer-events-none"
            />
          )}
          {own.row >= 0 && own.col >= 0 && (
            <rect
              {...box(own, -0.8)}
              fill="none"
              strokeWidth="1.8"
              className="stroke-foreground pointer-events-none"
            />
          )}
          {(focused || pointing) && (
            <rect
              {...box(active, -1.6)}
              fill="none"
              strokeWidth="1.6"
              className="stroke-brand pointer-events-none"
              data-testid="active-window"
            />
          )}
        </svg>
      </div>
      <p id={ids.readout} aria-live="polite" className="text-sm leading-6">
        {describeCell(sweep, direction, active)}
      </p>
      <p id={ids.keys} className="text-muted-foreground text-xs">
        {t.keys}
      </p>

      <ul className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <Key swatch={<span className="size-3 rounded-sm bg-(--sweep-holds)" />}>
          {t.shows[direction ?? "none"]}
        </Key>
        <Key swatch={<span className="size-3 rounded-sm" style={HATCH} />}>
          {t.showsNot[direction ?? "none"]}
        </Key>
        <Key swatch={<span className="size-3 rounded-sm bg-(--sweep-empty)" />}>
          {t.legend.empty}
        </Key>
        <Key swatch={<span className="border-foreground size-3 border-2" />}>
          {t.legend.own}
        </Key>
        {near && (
          <Key
            swatch={
              <span className="border-foreground size-3 border border-dashed" />
            }
          >
            {t.legend.near}
          </Key>
        )}
      </ul>

      <div>
        <button
          type="button"
          aria-expanded={table}
          aria-controls={ids.table}
          onClick={() => setTable((open) => !open)}
          className="text-brand text-sm font-medium underline underline-offset-4"
        >
          {table ? t.hideTable : t.showTable}
        </button>
      </div>
      <div id={ids.table} hidden={!table}>
        {table && <WindowTable sweep={sweep} direction={direction} own={own} />}
      </div>
    </section>
  );
}

function label(own: boolean): string {
  return own
    ? "fill-foreground text-[8px] font-semibold"
    : "fill-muted-foreground text-[8px]";
}

function Key({ swatch, children }: { swatch: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-center gap-1.5">
      <span aria-hidden className="flex">
        {swatch}
      </span>
      {children}
    </li>
  );
}

/** Every window as a table: start years by end years, each figure marked holds or not. */
function WindowTable({
  sweep,
  direction,
  own,
}: {
  sweep: Sweep;
  direction: Direction | null;
  own: Cell;
}) {
  // Rows and columns with at least one window: no empty last start or first end.
  const rows = sweep.starts
    .map((_, row) => row)
    .filter((row) =>
      sweep.ends.some((_, col) => cellState(sweep, { row, col }) !== "none"),
    );
  const cols = sweep.ends
    .map((_, col) => col)
    .filter((col) =>
      sweep.starts.some((_, row) => cellState(sweep, { row, col }) !== "none"),
    );
  return (
    <div
      role="region"
      aria-label={t.tableLabel}
      tabIndex={0}
      className="focus-visible:ring-brand overflow-x-auto rounded-xl border outline-none [contain:inline-size] focus-visible:ring-2"
    >
      <table className="text-xs tabular-nums">
        <caption className="text-muted-foreground p-3 text-start">
          {t.tableCaption(windowUnit(sweep))}{" "}
          {`✓ ${t.shows[direction ?? "none"]}. ✗ ${t.showsNot[direction ?? "none"]}.`}
        </caption>
        <thead>
          <tr>
            <td />
            {cols.map((col) => (
              <th
                key={col}
                scope="col"
                className="px-2 py-1 font-medium whitespace-nowrap"
              >
                {formatPeriod(sweep.ends[col])}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row} className="border-t">
              <th
                scope="row"
                className="px-2 py-1 text-start font-medium whitespace-nowrap"
              >
                {formatPeriod(sweep.starts[row])}
              </th>
              {cols.map((col) => (
                <WindowTableCell
                  key={col}
                  sweep={sweep}
                  at={{ row, col }}
                  own={own.row === row && own.col === col}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WindowTableCell({
  sweep,
  at,
  own,
}: {
  sweep: Sweep;
  at: Cell;
  own: boolean;
}) {
  const state = cellState(sweep, at);
  const near = isNear(sweep, at);
  const className = `px-2 py-1 text-end whitespace-nowrap ${near ? "bg-muted" : ""}`;
  if (state === "none") return <td className={className} />;
  if (state === "empty") return <td className={className}>—</td>;
  const figure = windowNumber(sweep, sweep.values[at.row][at.col] as number);
  const content = (
    <>
      {figure} <span aria-hidden>{state === "holds" ? "✓" : "✗"}</span>
      <span className="sr-only">
        {state === "holds" ? t.holdsWord : t.failsWord}
        {own && `, ${t.ownWord}`}
      </span>
    </>
  );
  return (
    <td className={className} data-own={own || undefined}>
      {own ? <strong>{content}</strong> : content}
    </td>
  );
}
