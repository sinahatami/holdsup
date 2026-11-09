import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import { strings } from "@/lib/strings";

const s = strings.home.sample;

/** One stage of the receipt. From a container 42rem wide it is a column, with a chevron to the next. */
function Stage({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="relative flex flex-col gap-1 @2xl:pe-4 @2xl:not-last:after:absolute @2xl:not-last:after:-inset-e-1 @2xl:not-last:after:top-1.5 @2xl:not-last:after:size-2 @2xl:not-last:after:rotate-45 @2xl:not-last:after:border-e-2 @2xl:not-last:after:border-t-2 @2xl:not-last:after:border-brand/70">
      <dt className="text-muted-foreground text-xs font-semibold tracking-widest uppercase">
        {label}
      </dt>
      <dd className="text-sm leading-6">{children}</dd>
    </div>
  );
}

/**
 * A fixed example of what a check returns: claim, official series, recomputed
 * value, verdict. When `href` is given (a real check of this same claim), the
 * whole card opens that receipt.
 */
export function SampleReceipt({ href }: { href?: string }) {
  return (
    <section aria-labelledby="sample-heading" className="@container">
      <figure
        className={`glass relative flex flex-col gap-4 rounded-2xl p-5 ${href ? "hover:border-brand/50 transition hover:-translate-y-0.5 hover:shadow-(--shadow-lift)" : ""}`}
      >
        <figcaption className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2
            id="sample-heading"
            className="text-muted-foreground text-xs font-semibold tracking-widest uppercase"
          >
            {s.heading}
          </h2>
          {href && (
            <Link
              href={href}
              className="text-brand inline-flex items-center gap-1.5 text-sm font-semibold after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
            >
              {s.open}
              <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
            </Link>
          )}
        </figcaption>
        <dl className="grid gap-4 @md:grid-cols-2 @2xl:grid-cols-[1.4fr_1.35fr_1.15fr_auto] @2xl:gap-5">
          <Stage label={s.claimLabel}>{s.claim}</Stage>
          <Stage label={s.seriesLabel}>
            <span className="font-medium">{s.series}</span>
            <span className="text-muted-foreground block">{s.source}</span>
          </Stage>
          <Stage label={s.recomputedLabel}>
            <span className="font-medium">{s.recomputed}</span>
            <span className="text-muted-foreground block">
              {s.recomputedNote}
            </span>
          </Stage>
          <Stage label={s.verdictLabel}>
            <VerdictBadge label={s.verdict} />
          </Stage>
        </dl>
      </figure>
    </section>
  );
}
