import { ArrowRight } from "lucide-react";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { sourceName } from "@/lib/format";
import { countHolding } from "@/lib/gallery";
import { headlineFigure } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.home.card;

const figure = "text-foreground font-semibold tabular-nums";

/**
 * What one claim was checked against: the figure it states beside the official one and
 * where that comes from, or the statistic alone when there is no single figure.
 */
function Figures({ claim: c }: { claim: ClaimResult }) {
  const head = headlineFigure(c);
  const source = c.data ? sourceName(c.data.source) : null;
  if (head) {
    const where = [source, head.period].filter(Boolean).join(", ");
    return (
      <p className="text-muted-foreground text-[0.9375rem] leading-6">
        {t.claimed} <span className={figure}>{head.claimed}</span>
        <ArrowRight
          className="mx-1 inline size-3.5 rtl:rotate-180"
          aria-hidden
        />{" "}
        {t.official} <span className={figure}>{head.official}</span>
        {where && <span className="block text-sm">{where}</span>}
      </p>
    );
  }
  const against =
    shownLabel(c) !== "cant_check" && c.indicator
      ? t.checkedAgainst(
          source ? `${c.indicator.name} (${source})` : c.indicator.name,
        )
      : t.noFigure;
  return (
    <p className="text-muted-foreground text-[0.9375rem] leading-6">
      {against}
    </p>
  );
}

/**
 * A finished check, small enough for an iframe on another site. One claim gets its stamp,
 * its words, the figures and why; several get a count of how many hold up, then each
 * claim with its own stamp and figures. Every number comes from the stored result.
 */
export function VerdictWidget({ result }: { result: CheckResult }) {
  const { claims } = result;
  if (claims.length === 1) {
    const [c] = claims;
    const why = c.explanation || c.verdict.reason;
    return (
      <article
        aria-label={c.claim.quote}
        className="flex flex-col items-start gap-3"
      >
        <VerdictBadge label={shownLabel(c)} large />
        <q className="font-heading text-xl leading-7">{c.claim.quote}</q>
        <Figures claim={c} />
        {why && <p className="line-clamp-3 leading-6">{why}</p>}
      </article>
    );
  }
  const { holds, total } = countHolding(
    claims.map((c) => ({ label: shownLabel(c) })),
  );
  return (
    <div className="flex flex-col gap-3">
      <p className="font-semibold">{t.summary(holds, total)}</p>
      <ul className="flex flex-col gap-4">
        {claims.map((c) => (
          <li key={c.index} className="flex flex-col items-start gap-1.5">
            <VerdictBadge label={shownLabel(c)} />
            <q className="font-heading line-clamp-2 text-[1.0625rem] leading-6">
              {c.claim.quote}
            </q>
            <Figures claim={c} />
          </li>
        ))}
      </ul>
    </div>
  );
}
