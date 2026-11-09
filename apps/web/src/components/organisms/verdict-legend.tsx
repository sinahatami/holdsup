import Link from "next/link";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { Label } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.legend;

/** The verdicts in the order a reader meets them, from the best to "can't check". */
const ORDER: Label[] = [
  "supported",
  "supported_framing_matters",
  "partly_supported",
  "not_supported",
  "cant_check",
];

/** The five verdicts and the rule behind each, in the order a reader meets them. */
export function VerdictRules({
  present = [],
  threshold,
  windows,
}: {
  /** The verdicts to mark "On this page", in words. */
  present?: readonly Label[];
  /** The share of time windows (a whole percent) a claim must hold in, if recorded. */
  threshold: number | null;
  /** Whether verdicts compared other time windows, which not every check does yet. */
  windows: boolean;
}) {
  const rules: Record<Label, string> = {
    supported: t.holds(threshold, windows),
    supported_framing_matters: t.framing(threshold, windows),
    partly_supported: t.partly,
    not_supported: t.fails,
    cant_check: t.cant,
  };
  return (
    <dl className="flex flex-col gap-4">
      {ORDER.map((label) => (
        <div key={label} className="flex flex-col gap-1.5">
          <dt className="flex flex-wrap items-center gap-2">
            <VerdictBadge label={label} />
            {present.includes(label) && (
              <span className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                {t.onThisPage}
              </span>
            )}
          </dt>
          <dd className="text-sm leading-6">{rules[label]}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * What each verdict means and where the lines are drawn: the allowed gap and the
 * share of time windows a claim must hold in. It marks the verdicts this page
 * uses, in words, so the reader can find their own among five.
 */
export function VerdictLegend({
  present,
  threshold,
  windows,
  tolerancesVersion,
}: {
  /** The verdicts of the claims on the page. */
  present: readonly Label[];
  /** The share of time windows (a whole percent) a claim must hold in, if recorded. */
  threshold: number | null;
  /** Whether those verdicts compared other time windows, which not every check does yet. */
  windows: boolean;
  tolerancesVersion: number;
}) {
  return (
    <section
      aria-labelledby="legend-heading"
      className="glass flex flex-col gap-5 rounded-2xl p-5 sm:p-6"
    >
      <h2 id="legend-heading" className="text-lg font-semibold">
        {t.heading}
      </h2>
      <VerdictRules present={present} threshold={threshold} windows={windows} />
      <div className="flex flex-col gap-1.5 border-t pt-4 text-sm leading-6">
        <h3 className="font-semibold">{t.gapHeading}</h3>
        <p>{t.gap}</p>
        <p className="text-muted-foreground">
          {t.version(tolerancesVersion)}{" "}
          <Link
            href={routes.methodology}
            className="text-brand font-medium underline underline-offset-4"
          >
            {t.method}
          </Link>
        </p>
      </div>
    </section>
  );
}
