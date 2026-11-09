import type { Tolerances, ValueTolerance } from "@/lib/api/client";
import { allowsNoGap, gapTerms, percentText } from "@/lib/methodology";
import { strings } from "@/lib/strings";

const g = strings.methodology.gaps;
type Kind = keyof typeof g.kinds;
const kinds = Object.keys(g.kinds) as Kind[];
const list = new Intl.ListFormat("en", { type: "conjunction" });

/** One kind's allowed gap in words, built from the rule's own numbers. */
function gapSentence(kind: Kind, tolerance: ValueTolerance): string {
  const terms = gapTerms(tolerance);
  if (allowsNoGap(terms)) return g.exact;
  const parts: string[] = [];
  if (terms.relative) parts.push(g.relative(terms.relative));
  if (terms.absolute !== null) {
    parts.push(g.absolute(terms.absolute, g.units[kind] ?? ""));
  }
  if (terms.rounding) parts.push(g.rounding);
  const joined = list.format(parts);
  const main =
    parts.length === 1
      ? `${joined.charAt(0).toUpperCase()}${joined.slice(1)}.`
      : g.largest(joined);
  return terms.plus ? `${main} ${g.plus(terms.plus)}` : main;
}

/** How near the nearest period may be, for each frequency the catalog uses. */
function periodGap(gaps: Tolerances["max_period_gap"]): string {
  const parts = Object.entries(gaps)
    .filter(([frequency]) => frequency in g.periodUnit)
    .map(([frequency, n]) =>
      g.periodFor(g.periodUnit[frequency](n), g.periodKind[frequency]),
    );
  return list.format(parts);
}

/** The allowed gap for each kind of figure, and the other thresholds, as the checks use them now. */
export function AllowedGaps({ tolerances: tol }: { tolerances: Tolerances }) {
  return (
    <div className="flex flex-col gap-6">
      <p className="leading-7">{g.intro(tol.version)}</p>
      <section aria-labelledby="gaps-kinds" className="flex flex-col gap-3">
        <h3 id="gaps-kinds" className="font-semibold">
          {g.kindsHeading}
        </h3>
        <dl className="flex flex-col gap-3">
          {kinds.map((kind) => (
            <div key={kind} className="glass rounded-2xl p-4">
              <dt className="flex flex-col gap-0.5">
                <span className="font-medium">{g.kinds[kind].label}</span>
                <span className="text-muted-foreground text-sm">
                  {g.kinds[kind].example}
                </span>
              </dt>
              <dd className="mt-2 text-sm leading-6">
                {gapSentence(kind, tol.values[kind])}
              </dd>
            </div>
          ))}
        </dl>
      </section>
      <section aria-labelledby="gaps-others" className="flex flex-col gap-2">
        <h3 id="gaps-others" className="font-semibold">
          {g.othersHeading}
        </h3>
        <ul className="list-disc ps-5 text-sm leading-6">
          <li>{g.flat(percentText(tol.flat_relative))}</li>
          <li>{g.trend(percentText(tol.trend_min_r2))}</li>
          <li>{g.periodGap(periodGap(tol.max_period_gap))}</li>
        </ul>
      </section>
    </div>
  );
}
