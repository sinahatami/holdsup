import { ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { GalleryClaim, GalleryItem } from "@/lib/api/client";
import { formatFigures, sourceName } from "@/lib/format";
import { countHolding } from "@/lib/gallery";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.home.card;

const figure = "text-foreground font-semibold tabular-nums";

/**
 * What one claim was checked against: the number it stated beside the official
 * one, and where that comes from. A claim with no single figure (a trend, a
 * claim that could not be checked) says what it was checked against instead.
 */
function Figures({ claim: c }: { claim: GalleryClaim }) {
  const where = [c.source && sourceName(c.source), c.period]
    .filter(Boolean)
    .join(", ");
  if (c.claimed != null && c.official != null) {
    const n = formatFigures(c.claimed, c.official, c.unit);
    return (
      <p className="text-muted-foreground text-[0.9375rem] leading-6">
        {t.claimed} <span className={figure}>{n.claimed}</span>
        <ArrowRight
          className="mx-1 inline size-3.5 rtl:rotate-180"
          aria-hidden
        />{" "}
        {t.official} <span className={figure}>{n.official}</span>
        {where && <span className="block text-sm">{where}</span>}
      </p>
    );
  }
  const against =
    c.label !== "cant_check" && c.indicator
      ? t.checkedAgainst(
          c.source ? `${c.indicator} (${sourceName(c.source)})` : c.indicator,
        )
      : t.noFigure;
  return (
    <p className="text-muted-foreground text-[0.9375rem] leading-6">
      {against}
    </p>
  );
}

/**
 * A featured check: its text (the whole card is the link), then each claim with
 * its own verdict and numbers. With several claims, each is named by its quote
 * and a summary says how many hold up, so no badge stands alone.
 */
export function GalleryCard({ item }: { item: GalleryItem }) {
  const claims = item.claims ?? [];
  const several = claims.length > 1;
  const { holds, total } = countHolding(claims);
  return (
    <li className="glass group hover:border-brand/50 relative flex flex-col gap-4 rounded-2xl p-5 transition hover:-translate-y-1 hover:shadow-(--shadow-lift)">
      <Link
        className="flex items-start justify-between gap-3 text-[1.0625rem] leading-7 font-medium after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
        href={routes.check(item.id)}
      >
        <span>{item.text}</span>
        <ArrowUpRight
          className="text-muted-foreground group-hover:text-brand mt-1 size-5 shrink-0 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          aria-hidden
        />
      </Link>
      {several && (
        <p className="text-sm font-semibold">{t.summary(holds, total)}</p>
      )}
      {claims.length === 0 ? (
        // An API that predates per-claim data: the verdicts alone.
        <div className="flex flex-wrap gap-2">
          {item.verdicts.map((v, i) => (
            <VerdictBadge key={i} label={v} />
          ))}
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {claims.map((c, i) => (
            <li key={i} className="flex flex-col items-start gap-2">
              <VerdictBadge label={c.label} />
              {several && (
                <q className="line-clamp-2 text-[0.9375rem] leading-6">
                  {c.quote}
                </q>
              )}
              <Figures claim={c} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
