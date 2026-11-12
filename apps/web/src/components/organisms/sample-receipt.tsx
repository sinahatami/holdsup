import { ArrowRight, ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const s = strings.home.sample;

/**
 * One stage of the receipt: a label, then what it holds. From a container 42rem wide the
 * four stages are equal columns; narrower, they stack. The chevron to the next stage sits
 * in the label row (inside the gap on a wide card, below the stage on a narrow one) so it
 * is level with the labels, and it turns to point down when the stages stack.
 */
function Stage({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="group/stage relative flex min-w-0 flex-col gap-1.5">
      <dt className="text-muted-foreground flex h-4 items-center text-xs font-semibold tracking-widest uppercase">
        {label}
        <span
          aria-hidden
          className="text-muted-foreground/70 absolute inset-x-0 -bottom-7 flex h-7 items-center justify-center group-last/stage:hidden @2xl:inset-x-auto @2xl:top-0 @2xl:-inset-e-6 @2xl:bottom-auto @2xl:h-4 @2xl:w-6"
        >
          <ChevronRight className="size-4 rotate-90 @2xl:rotate-0 @2xl:rtl:rotate-180" />
        </span>
      </dt>
      <dd className="flex flex-col items-start gap-0.5 text-sm leading-5">
        {children}
      </dd>
    </div>
  );
}

/** "11.9% → 7.7%". The arrow is for the eye; a screen reader hears "11.9% to 7.7%". */
function Range({
  from,
  to,
  className,
}: {
  from: string;
  to: string;
  className: string;
}) {
  return (
    <span
      className={cn(
        "text-base leading-6 whitespace-nowrap tabular-nums",
        className,
      )}
    >
      {from}
      <span aria-hidden> → </span>
      <span className="sr-only"> to </span>
      {to}
    </span>
  );
}

/**
 * A fixed example of what a check returns: claim, official series, recomputed
 * value, verdict. When `href` is given (a real check of this same claim), the
 * card closes with a link to that receipt and the whole card opens it.
 */
export function SampleReceipt({ href }: { href?: string }) {
  return (
    <section aria-labelledby="sample-heading" className="@container">
      {/* Quieter than the claim box on purpose: no shadow, a light edge, a flat tint. */}
      <figure
        className={cn(
          "bg-muted/40 border-border relative flex flex-col gap-5 rounded-2xl border p-5",
          href && "hover:border-foreground/30 transition",
        )}
      >
        <figcaption className="flex flex-col gap-0.5">
          <h2
            id="sample-heading"
            className="text-muted-foreground text-xs font-semibold tracking-widest uppercase"
          >
            {s.heading}
          </h2>
          <p className="text-muted-foreground text-xs">{s.note}</p>
        </figcaption>
        <dl className="grid grid-cols-1 gap-y-7 @2xl:grid-cols-4 @2xl:gap-x-6">
          <Stage label={s.claimLabel}>
            {/* The claimed figures sit beside the recomputed ones, in a lighter weight. */}
            <Range
              from={s.claimed.from}
              to={s.claimed.to}
              className="font-medium"
            />
            <span className="text-muted-foreground">{s.claimNote}</span>
          </Stage>
          <Stage label={s.seriesLabel}>
            <span className="font-medium">{s.series}</span>
            <span className="text-muted-foreground">{s.source}</span>
          </Stage>
          <Stage label={s.recomputedLabel}>
            <Range
              from={s.recomputed.from}
              to={s.recomputed.to}
              className="font-bold"
            />
            <span className="text-muted-foreground">{s.recomputedNote}</span>
          </Stage>
          <Stage label={s.verdictLabel}>
            <VerdictBadge label={s.verdict} />
          </Stage>
        </dl>
        {href && (
          <div className="border-border border-t pt-3">
            <Link
              href={href}
              className="text-foreground decoration-foreground/30 hover:decoration-foreground inline-flex items-center gap-1.5 text-sm font-semibold underline underline-offset-4 after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
            >
              {s.open}
              <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
            </Link>
          </div>
        )}
      </figure>
    </section>
  );
}
