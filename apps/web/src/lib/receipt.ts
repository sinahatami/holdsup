import type {
  CheckResult,
  ClaimResult,
  ClaimSpec,
  Operation,
  Part,
} from "@/lib/api/client";
import {
  formatAmount,
  formatFigures,
  formatPeriod,
  placeName,
  sourceName,
} from "@/lib/format";
import { strings } from "@/lib/strings";

type Basis = NonNullable<ClaimSpec["geo_basis"]>;

const reading = strings.receipt.reading;
const compared = strings.receipt.compared;

/** One line of "How HoldsUp read the claim": what was understood, and how sure. */
export interface ReadingRow {
  label: string;
  value: string;
  /** How the value came to be, when it was not simply written in the claim. */
  note?: string;
}

/** A basis worth saying: everything but "stated", which is the ordinary case. */
const unusual = (basis: Basis | null): Exclude<Basis, "stated"> | null =>
  basis && basis !== "stated" ? basis : null;

/** How a value came to be, in words; undefined when it was simply stated. */
function basisText(basis: Basis | null): string | undefined {
  const b = unusual(basis);
  return b ? reading.basis[b] : undefined;
}

/** A figure as the claim wrote it: "12 points", "44%", "2.9 billion euros". */
function written(n: number, unit: string | null): string {
  const amount = formatAmount(n);
  if (!unit) return amount;
  return unit === "%" ? `${amount}%` : `${amount} ${unit}`;
}

function periodRow(spec: ClaimSpec): ReadingRow | null {
  const { start, end } = spec;
  if (!start && !end) return null;
  let value: string;
  if (start && end && start !== end) {
    value = reading.periodRange(formatPeriod(start), formatPeriod(end));
  } else if (start && !end) {
    value = reading.periodFrom(formatPeriod(start));
  } else {
    value = formatPeriod((end ?? start) as string);
  }
  const [s, e] = [basisText(spec.start_basis), basisText(spec.end_basis)];
  // One reason for both ends is said once.
  const notes =
    s && s === e
      ? [s]
      : [s && `${reading.start}: ${s}`, e && `${reading.end}: ${e}`];
  return {
    label: reading.period,
    value,
    note: notes.filter(Boolean).join("; ") || undefined,
  };
}

/**
 * What HoldsUp understood a claim to say, field by field, so a reader can see
 * whether it read the claim as meant. Only what the claim gave is listed.
 */
export function claimReading(spec: ClaimSpec): ReadingRow[] {
  const a = spec.assertion;
  const rows: (ReadingRow | null)[] = [
    { label: reading.statistic, value: spec.indicator_phrase },
    spec.geo
      ? {
          label: reading.place,
          value: placeName(spec.geo),
          note: basisText(spec.geo_basis),
        }
      : null,
    spec.peers.length
      ? {
          label: reading.comparedWith,
          value: spec.peers.map(placeName).join(", "),
        }
      : null,
    periodRow(spec),
    { label: reading.kind, value: reading.kinds[a.type] },
    a.direction
      ? { label: reading.direction, value: reading.directions[a.direction] }
      : null,
    a.value !== null
      ? {
          label: reading.figure,
          value: [reading.operators[a.operator], written(a.value, a.unit)]
            .filter(Boolean)
            .join(" "),
        }
      : null,
    a.start_value !== null && a.end_value !== null
      ? {
          label: reading.range,
          value: `${formatAmount(a.start_value)} → ${formatAmount(a.end_value)}`,
        }
      : a.end_value !== null
        ? { label: reading.endsAt, value: formatAmount(a.end_value) }
        : a.start_value !== null
          ? { label: reading.startsAt, value: formatAmount(a.start_value) }
          : null,
    spec.speaker
      ? {
          label: reading.saidBy,
          value: spec.said_on
            ? `${spec.speaker}, ${spec.said_on}`
            : spec.speaker,
        }
      : null,
  ];
  return rows.filter((r): r is ReadingRow => r !== null);
}

/** One compared part of a verdict, ready to show. */
export interface PartView {
  /** The API's name for the part: "assertion", "start value", "end value", "vs FR". */
  name: string;
  label: string;
  /** The period the official figure is for, in words. */
  period: string | null;
  holds: boolean;
  claimed: string;
  official: string;
  /** How far apart the two may be and still hold; null when no gap applies. */
  gap: string | null;
  note: string | null;
}

/** The operation that settles the claim, when the plan named one. */
export function decidingOp(c: ClaimResult): Operation | undefined {
  const first = (c.answer ?? [])[0];
  return first === undefined ? undefined : c.operations?.[first];
}

function partLabel(name: string): string {
  const labels = compared.parts as Record<string, unknown>;
  const known = labels[name];
  if (typeof known === "string") return known;
  const against = /^vs (.+)$/.exec(name);
  return against ? compared.parts.against(placeName(against[1])) : name;
}

/**
 * The unit a part's numbers are in. The claim's own figure is in the unit of the
 * calculation that settles it ("percentage points", "×" for a ratio); a stated
 * start or end value is a level of the series, so in the series' unit.
 */
function partUnit(c: ClaimResult, name: string): string | null {
  const series = c.indicator?.unit ?? null;
  if (name === "start value" || name === "end value") return series;
  if (name !== "assertion") return null;
  const deciding = decidingOp(c);
  if (!deciding) return series;
  return deciding.unit ?? (c.claim.assertion.type === "ratio" ? "×" : null);
}

// A bound ("more than 18%") has no gap: it holds or it does not.
const HAS_GAP = new Set(["about", "at_least", "at_most"]);

/** The gap a part allows either side of the claimed figure, or null for a bound. */
export function allowedGap(p: Part): number | null {
  return p.tolerance != null && HAS_GAP.has(p.operator) ? p.tolerance : null;
}

function gapText(gap: number | null, unit: string | null): string | null {
  return gap === null ? null : `±${formatFigures(gap, gap, unit).official}`;
}

function partView(c: ClaimResult, p: Part): PartView {
  const unit = partUnit(c, p.name);
  const base = {
    name: p.name,
    label: partLabel(p.name),
    period: p.period ? formatPeriod(p.period) : null,
    holds: p.holds,
  };
  if (p.asserted != null && p.computed != null) {
    const f = formatFigures(p.asserted, p.computed, unit);
    const word = reading.operators[p.operator];
    return {
      ...base,
      claimed: word ? `${word} ${f.claimed}` : f.claimed,
      official: f.official,
      gap: gapText(allowedGap(p), unit),
      note: null,
    };
  }
  // Only a direction was claimed ("fell"): there is no figure to hold it to.
  const direction = c.claim.assertion.direction;
  return {
    ...base,
    claimed: direction ? compared.directions[direction] : "—",
    official:
      p.computed != null
        ? formatFigures(p.computed, p.computed, unit).official
        : "—",
    gap: null,
    note: compared.directionOnly,
  };
}

/** What the verdict compared, one entry per checked part of the claim. */
export function comparison(c: ClaimResult): PartView[] {
  return (c.verdict.parts ?? []).map((p) => partView(c, p));
}

/** A dataset the claim's figures came from, with the link to the data itself. */
export interface SourceLink {
  label: string;
  url: string;
}

/** The datasets behind a claim's figures: the matched series, then any used besides it. */
export function sourceLinks(c: ClaimResult): SourceLink[] {
  const refs = [c.data, ...(c.extra_sources ?? []).map((e) => e.data)];
  return refs.flatMap((d) =>
    d ? [{ label: `${sourceName(d.source)} ${d.dataset}`, url: d.url }] : [],
  );
}

type ChangeKind = keyof typeof strings.receipt.recompute.ops.change;

/**
 * What a calculation does, in a sentence. Null when the call is not one HoldsUp
 * knows how to put in words; the receipt still shows the call itself.
 */
export function opGloss(op: Operation): string | null {
  const ops = strings.receipt.recompute.ops;
  const arg = (key: string) => {
    const v = op.args[key];
    return typeof v === "string" ? v : null;
  };
  const place = (key: string) => {
    const v = arg(key);
    return v === null ? null : placeName(v);
  };
  const when = (key: string) => {
    const v = arg(key);
    return v === null ? null : formatPeriod(v);
  };
  switch (op.op) {
    case "value_at": {
      const [p, w] = [place("geo"), when("period")];
      return p && w ? ops.value_at(p, w) : null;
    }
    case "change": {
      const kind = arg("kind");
      const [from, to] = [when("start"), when("end")];
      if (!kind || !(kind in ops.change) || !from || !to) return null;
      return ops.change[kind as ChangeKind](from, to);
    }
    case "cagr":
    case "trend": {
      const [from, to] = [when("start"), when("end")];
      return from && to ? ops[op.op](from, to) : null;
    }
    case "compare": {
      const [p, other, w] = [place("geo"), place("geo_b"), when("period")];
      return p && other && w ? ops.compare(p, other, w) : null;
    }
    case "rank": {
      const [p, w] = [place("geo"), when("period")];
      return p && w ? ops.rank(p, w) : null;
    }
    case "per_capita":
      return ops.per_capita;
    case "deflate": {
      const base = when("base");
      return base ? ops.deflate(base) : null;
    }
    default:
      return null;
  }
}

/** A stretch of the original text, and the claim it is the quote of (if any). */
export interface Segment {
  text: string;
  /** Position of the claim in the check's list; null for text between quotes. */
  claim: number | null;
}

/** The same text with case and curly quotes folded away, one character for one. */
const fold = (s: string) =>
  s
    .toLowerCase()
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"');

/**
 * Where a claim's quote sits in the text that was pasted, and how long the match
 * is. The quote was written down by the extraction step, so it can differ a
 * little from the text: in case, in curly against straight quotes, and in the
 * punctuation that closes it ("29%." where the text goes on "29%;").
 */
function find(text: string, quote: string): { at: number; len: number } | null {
  const exact = text.indexOf(quote);
  if (exact >= 0) return { at: exact, len: quote.length };
  const [haystack, needle] = [fold(text), fold(quote)];
  // Folding can change a text's length; only trust a position when it did not.
  if (haystack.length !== text.length) return null;
  for (const candidate of [needle, needle.replace(/[.;,:!?\u2026]+$/, "")]) {
    const at = candidate ? haystack.indexOf(candidate) : -1;
    if (at >= 0) return { at, len: candidate.length };
  }
  return null;
}

/**
 * Splits the text a person pasted at each claim's quote, so every quote can be
 * marked where it was said. A quote that cannot be found is left unmarked, and
 * of two that overlap the first is kept.
 */
export function annotate(text: string, quotes: readonly string[]): Segment[] {
  const found = quotes
    .flatMap((quote, claim) => {
      const hit = find(text, quote);
      return hit && hit.len > 0 ? [{ claim, ...hit }] : [];
    })
    .sort((a, b) => a.at - b.at);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const q of found) {
    if (q.at < cursor) continue;
    if (q.at > cursor) {
      segments.push({ text: text.slice(cursor, q.at), claim: null });
    }
    segments.push({ text: text.slice(q.at, q.at + q.len), claim: q.claim });
    cursor = q.at + q.len;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), claim: null });
  }
  return segments;
}

/**
 * Whether the pasted text says more than the claims' own quotes, so it is worth
 * showing beside them: when it holds several claims, or words around the one.
 */
export function hasMoreThanQuotes(
  text: string,
  quotes: readonly string[],
): boolean {
  if (quotes.length === 0) return false;
  const squash = (s: string) => s.replace(/\s+/g, " ").trim();
  return quotes.length > 1 || squash(text) !== squash(quotes[0]);
}

/**
 * The share of comparable time windows a claim must hold in to be "supported",
 * as the result recorded it (null if no claim carries one, as when nothing
 * could be checked). It is a whole percent, for the legend to say.
 */
export function framingPercent(result: CheckResult): number | null {
  const share = result.claims
    .map((c) => c.verdict.framing_threshold)
    .find((x) => x !== null && x !== undefined);
  return share === undefined || share === null ? null : Math.round(share * 100);
}

/** True when any claim's verdict compared other time windows (not every check does yet). */
export function windowsCompared(result: CheckResult): boolean {
  return result.claims.some(
    (c) =>
      c.verdict.window_share !== null && c.verdict.window_share !== undefined,
  );
}

/**
 * The one comparison a card or an image can state: the claim's own figure
 * ("fell 12 points") or, failing that, the end value it gives ("to 7.7%"), as
 * the gallery picks it. A claim with only a direction, a bound or no data has none.
 */
export function headlineFigure(c: ClaimResult): PartView | null {
  const figures = comparison(c).filter((p) => p.note === null);
  const byName = (name: string) => figures.find((p) => p.name === name);
  return byName("assertion") ?? byName("end value") ?? null;
}

/**
 * Why a claim could not be checked, for the help under its verdict: no statistic fits it, the
 * source has no figures for its place, or this kind of claim cannot be recomputed yet. A claim
 * that failed because something was briefly down is `temporary`; a result stored before the
 * step was recorded falls back to what the claim still shows. Null when it was checked.
 */
export type StopCause =
  "no_series" | "no_figures" | "unsupported" | "temporary" | "unknown";

export function stopCause(c: ClaimResult): StopCause | null {
  if (c.verdict.label !== "cant_check") return null;
  if (c.retryable) return "temporary";
  switch (c.stopped_at) {
    case "match":
      return "no_series";
    case "fetch":
      return "no_figures";
    case "plan":
    case "execute":
    case "verdict":
      return "unsupported";
    default:
      return c.indicator ? "unknown" : "no_series";
  }
}
