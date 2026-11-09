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
