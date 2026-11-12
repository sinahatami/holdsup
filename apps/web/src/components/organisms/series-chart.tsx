"use client";

import { scaleLinear } from "d3-scale";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { formatAmount, formatPeriod, placeName } from "@/lib/format";
import {
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
  type Chart,
} from "@/lib/series-chart";
import { strings } from "@/lib/strings";

const t = strings.chart;

// The chart's own units: its height with the axis band, and the room around the plot.
const HEIGHT = 220;
const TOP = 12;
const RIGHT = 14;
const BOTTOM = 26;
// Until the frame is measured (and in tests, which have no layout): a medium card.
const FALLBACK_WIDTH = 600;
// One x-axis label per this many pixels, at most.
const X_LABEL_ROOM = 64;
// Roughly the width of a digit at the axis' 11px, to make room for the longest value label.
const DIGIT = 6.6;

/**
 * The series the check read, as a line over time: the claim's window shaded, the values the
 * check used as dots, the values the claim states as hollow diamonds with their allowed gap,
 * and a trend's fitted line. Every number comes from the API; the scales only place them.
 * The picture is for the eye; the focusable frame takes the arrow keys and says each value
 * in words, and the table holds every value with its notes.
 */
export function SeriesChart({ chart }: { chart: Chart }) {
  const id = useId().replace(/[^\w-]/g, "");
  const ids = {
    heading: `${id}-heading`,
    readout: `${id}-readout`,
    keys: `${id}-keys`,
    table: `${id}-table`,
  };
  const { points } = chart;
  const [active, setActive] = useState(() => initialIndex(chart));
  const [focused, setFocused] = useState(false);
  const [pointing, setPointing] = useState(false);
  const [table, setTable] = useState(false);
  const [width, setWidth] = useState(FALLBACK_WIDTH);
  const frame = useRef<HTMLDivElement>(null);

  // The chart is drawn at the frame's own width, so its text stays the same size on a phone.
  useEffect(() => {
    const el = frame.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const measured = Math.round(entry.contentRect.width);
      if (measured > 0) setWidth(measured);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const y = scaleLinear().domain(valueExtent(chart)).nice();
  const yTicks = y.ticks(5);
  const yLabels = yTicks.map((v) => formatAmount(v));
  const left = 10 + DIGIT * Math.max(...yLabels.map((s) => s.length));
  y.range([HEIGHT - BOTTOM, TOP]);

  const first = points[0];
  const last = points[points.length - 1];
  const x = scaleLinear()
    .domain([first.time, last.time])
    .range([left, width - RIGHT]);
  const step = periodStep(points);
  // Whole years only: a short monthly series is labelled by its years, never by "2023.5".
  const xTicks = x
    .ticks(Math.max(2, Math.floor((width - left - RIGHT) / X_LABEL_ROOM)))
    .filter(Number.isInteger);

  const at = (period: string) => x(periodTime(period) ?? first.time);
  const band = chart.window && {
    x: at(chart.window.start),
    width: at(chart.window.end) - at(chart.window.start),
  };
  const current = points[active];

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const next = movePoint(active, e.key, points.length);
    if (next === null) return;
    e.preventDefault();
    setActive(next);
  };
  const pick = (e: PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!box || box.width === 0) return;
    const px = ((e.clientX - box.left) * width) / box.width;
    setActive(nearestIndex(points, x.invert(px)));
  };

  return (
    <section aria-labelledby={ids.heading} className="flex flex-col gap-3">
      <Eyebrow as="h3" id={ids.heading}>
        {t.heading}
      </Eyebrow>
      <p className="leading-7">
        {t.summary(
          placeName(chart.geo),
          formatPeriod(first.period),
          formatPeriod(last.period),
          unitText(chart),
        )}
        {chart.window &&
          ` ${t.window(formatPeriod(chart.window.start), formatPeriod(chart.window.end))}`}
      </p>
      <p className="text-muted-foreground text-sm leading-6">{t.asRead}</p>

      <div
        ref={frame}
        role="group"
        dir="ltr" // time runs left to right in any language
        tabIndex={0}
        aria-label={t.chartLabel}
        aria-describedby={`${ids.keys} ${ids.readout}`}
        onKeyDown={onKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="focus-visible:ring-brand rounded-lg outline-none [contain:inline-size] focus-visible:ring-2"
      >
        <svg
          aria-hidden
          width={width}
          height={HEIGHT}
          viewBox={`0 0 ${width} ${HEIGHT}`}
          className="block max-w-full"
          data-testid="series-chart"
        >
          {band && (
            <rect
              data-testid="chart-window"
              x={band.x}
              y={TOP}
              width={band.width}
              height={HEIGHT - BOTTOM - TOP}
              className="fill-(--chart-window)"
            />
          )}
          {yTicks.map((v, i) => (
            <g key={v}>
              <line
                x1={left}
                x2={width - RIGHT}
                y1={y(v)}
                y2={y(v)}
                strokeWidth="1"
                className="stroke-border"
              />
              <text
                x={left - 6}
                y={y(v) + 4}
                textAnchor="end"
                className="fill-muted-foreground text-[11px] tabular-nums"
              >
                {yLabels[i]}
              </text>
            </g>
          ))}
          {xTicks.map((v) => (
            <text
              key={v}
              x={x(v)}
              y={HEIGHT - 8}
              textAnchor="middle"
              className="fill-muted-foreground text-[11px] tabular-nums"
            >
              {v}
            </text>
          ))}
          <path
            d={linePath(points, step, x, y)}
            fill="none"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            className="stroke-(--chart-used)"
            data-testid="chart-line"
          />
          {chart.fit && chart.window && (
            <line
              data-testid="chart-fit"
              x1={at(chart.window.start)}
              y1={y(chart.fit.start)}
              x2={at(chart.window.end)}
              y2={y(chart.fit.end)}
              strokeWidth="2"
              strokeDasharray="6 4"
              className="stroke-foreground"
            />
          )}
          {chart.used.map((period) => {
            const p = points.find((q) => q.period === period);
            return (
              p && (
                <circle
                  key={period}
                  data-used={period}
                  cx={x(p.time)}
                  cy={y(p.value)}
                  r="4.5"
                  strokeWidth="2"
                  className="fill-(--chart-used) stroke-background"
                />
              )
            );
          })}
          {chart.claimed.map((m) => {
            const cx = at(m.period);
            const cy = y(m.value);
            return (
              <g key={`${m.period}-${m.value}`} data-claimed={m.period}>
                {m.gap !== null && (
                  <path
                    d={`M${cx - 4},${y(m.value + m.gap)}h8M${cx},${y(m.value + m.gap)}V${y(m.value - m.gap)}M${cx - 4},${y(m.value - m.gap)}h8`}
                    strokeWidth="1.5"
                    className="stroke-(--chart-claimed)"
                  />
                )}
                <path
                  d={`M${cx},${cy - 6}l6,6l-6,6l-6,-6z`}
                  strokeWidth="2"
                  className="fill-background stroke-(--chart-claimed)"
                />
              </g>
            );
          })}
          {(focused || pointing) && current && (
            <g data-testid="active-point" className="pointer-events-none">
              <line
                x1={x(current.time)}
                x2={x(current.time)}
                y1={TOP}
                y2={HEIGHT - BOTTOM}
                strokeWidth="1"
                className="stroke-muted-foreground"
              />
              <circle
                cx={x(current.time)}
                cy={y(current.value)}
                r="6"
                fill="none"
                strokeWidth="2"
                className="stroke-brand"
              />
            </g>
          )}
          <rect
            x={left}
            y={TOP}
            width={Math.max(0, width - RIGHT - left)}
            height={HEIGHT - BOTTOM - TOP}
            fill="transparent"
            onPointerMove={pick}
            onPointerDown={pick}
            onPointerEnter={() => setPointing(true)}
            onPointerLeave={() => setPointing(false)}
          />
        </svg>
      </div>
      <p id={ids.readout} aria-live="polite" className="text-sm leading-6">
        {describePoint(chart, active)}
      </p>
      <p id={ids.keys} className="text-muted-foreground text-xs">
        {t.keys}
      </p>

      <ul className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <Key
          swatch={<span className="h-0.5 w-4 rounded-full bg-(--chart-used)" />}
        >
          {t.legend.line}
        </Key>
        {chart.window && (
          <Key
            swatch={<span className="h-3 w-4 rounded-sm bg-(--chart-window)" />}
          >
            {t.legend.window}
          </Key>
        )}
        {chart.used.length > 0 && (
          <Key
            swatch={
              <span className="size-2.5 rounded-full bg-(--chart-used)" />
            }
          >
            {t.legend.used}
          </Key>
        )}
        {chart.claimed.length > 0 && (
          <Key
            swatch={
              <span className="size-2.5 rotate-45 border-2 border-(--chart-claimed)" />
            }
          >
            {t.legend.claimed}
          </Key>
        )}
        {chart.fit && (
          <Key
            swatch={
              <span className="border-foreground w-4 border-t-2 border-dashed" />
            }
          >
            {t.legend.fit}
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
        {table && <SeriesTable chart={chart} />}
      </div>
    </section>
  );
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

/** Every value as a table, with what the chart marks about it. */
function SeriesTable({ chart }: { chart: Chart }) {
  return (
    <div
      role="region"
      aria-label={t.tableLabel}
      tabIndex={0}
      className="focus-visible:ring-brand max-h-96 overflow-auto rounded-xl border outline-none [contain:inline-size] focus-visible:ring-2"
    >
      <table className="w-full text-sm">
        <caption className="text-muted-foreground p-3 text-start text-xs">
          {t.tableCaption(unitText(chart))}
        </caption>
        <thead>
          <tr>
            <th scope="col" className="px-3 py-1.5 text-start font-medium">
              {t.columns.period}
            </th>
            <th scope="col" className="px-3 py-1.5 text-end font-medium">
              {t.columns.value}
            </th>
            <th scope="col" className="px-3 py-1.5 text-start font-medium">
              {t.columns.notes}
            </th>
          </tr>
        </thead>
        <tbody>
          {chart.points.map((p) => (
            <tr key={p.period} className="border-t">
              <th
                scope="row"
                className="px-3 py-1.5 text-start font-medium whitespace-nowrap"
              >
                {formatPeriod(p.period)}
              </th>
              <td className="px-3 py-1.5 text-end whitespace-nowrap tabular-nums">
                {formatAmount(p.value)}
              </td>
              <td className="text-muted-foreground px-3 py-1.5">
                {pointNotes(chart, p.period).join(" ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
