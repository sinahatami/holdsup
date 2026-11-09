import { strings } from "@/lib/strings";

/** A computed number as the receipt shows it: up to 10 significant digits, "—" when absent. */
export function formatNumber(n: number | null | undefined): string {
  return n === null || n === undefined
    ? "—"
    : String(Number(n.toPrecision(10)));
}

/** An operation call as code, e.g. `change(start="2015", end="2023")`. */
export function formatCall(op: string, args: Record<string, unknown>): string {
  const list = Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
  return `${op}(${list})`;
}

const figureFormat = new Intl.NumberFormat(strings.locale, {
  maximumFractionDigits: 2,
});

/** A figure and its unit: "42.7% of labour force", "-4.34 percentage points". */
export function withUnit(
  value: string,
  unit: string | null | undefined,
): string {
  if (!unit) return value;
  return unit.startsWith("%") ? `${value}${unit}` : `${value} ${unit}`;
}

/** A figure as a sentence shows it: grouped digits, at most two decimals ("1,234.57"). */
export function formatAmount(n: number): string {
  return figureFormat.format(n);
}

/**
 * The two numbers of a card's "Claimed X, official Y", each with a short unit:
 * "60%" and "7.2%", "-12 points" and "-10.7 points", "2×" and "1.93×". A unit
 * too long to say twice ("live births per woman") follows only the second
 * number; "% per year" puts its "%" on both. The receipt has the full unit.
 */
export function formatFigures(
  claimed: number,
  official: number,
  unit: string | null | undefined,
): { claimed: string; official: string } {
  const a = figureFormat.format(claimed);
  const b = figureFormat.format(official);
  if (!unit) return { claimed: a, official: b };
  if (unit === "×") return { claimed: `${a}×`, official: `${b}×` };
  if (unit === "percentage points") {
    return { claimed: `${a} points`, official: `${b} points` };
  }
  if (unit === "%" || unit.startsWith("% of")) {
    return { claimed: `${a}%`, official: `${b}%` };
  }
  return unit.startsWith("%")
    ? { claimed: `${a}%`, official: `${b}${unit}` }
    : { claimed: a, official: `${b} ${unit}` };
}

/**
 * A source as a heading or tag reads it. Takes the gallery's id ("worldbank")
 * or the catalog's label, which is written for a sentence ("the World Bank").
 */
export function sourceName(source: string): string {
  const known = (strings.sources as Record<string, string>)[source];
  return known ?? source.replace(/^the /i, "");
}

const monthYear = new Intl.DateTimeFormat(strings.locale, {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const PERIOD = /^(\d{4})(?:-(0[1-9]|1[0-2])|-Q([1-4])|-S([12]))?$/;

/**
 * A period code as words: "2014-02" is "February 2014", "2025-Q1" is "Q1 2025",
 * "2025-S2" is "the second half of 2025", "latest" is "the latest period". A
 * plain year stays as it is, and anything else is shown as it came.
 */
export function formatPeriod(period: string): string {
  if (period === "latest") return strings.periods.latest;
  const m = PERIOD.exec(period);
  if (!m) return period;
  const [, year, month, quarter, half] = m;
  if (month) return monthYear.format(new Date(Date.UTC(+year, +month - 1, 1)));
  if (quarter) return strings.periods.quarter(quarter, year);
  if (half) return strings.periods.half(half, year);
  return year;
}

const day = new Intl.DateTimeFormat(strings.locale, {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const clock = new Intl.DateTimeFormat(strings.locale, {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
});

/** A timestamp from the API as a date, or null. Sources write offsets as "+0100", which not every browser reads without the colon. */
function parseTimestamp(iso: string): Date | null {
  const date = new Date(iso.replace(/([+-]\d{2})(\d{2})$/, "$1:$2"));
  return Number.isNaN(date.getTime()) ? null : date;
}

/** A timestamp as "November 7, 2026, 16:45 UTC". Text that is not a date is shown as it came. */
export function formatTimestamp(iso: string): string {
  const date = parseTimestamp(iso);
  return date ? `${day.format(date)}, ${clock.format(date)} UTC` : iso;
}

/** A timestamp as its UTC day, "November 7, 2026". Text that is not a date is shown as it came. */
export function formatDate(iso: string): string {
  const date = parseTimestamp(iso);
  return date ? day.format(date) : iso;
}

const countries = new Intl.DisplayNames(strings.locale, { type: "region" });

/**
 * A claim's place code as a name: "IT" is "Italy", "EA" is "Euro area". A code
 * that is neither is shown as it is.
 */
export function placeName(code: string): string {
  const group = (strings.places as Record<string, string>)[code];
  if (group) return group;
  try {
    return countries.of(code) ?? code;
  } catch {
    return code; // not a region code at all
  }
}
