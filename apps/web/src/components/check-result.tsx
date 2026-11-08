import type { CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { Receipt } from "@/components/receipt";
import { VerdictBadge } from "@/components/verdict";

export function CheckResultView({ result }: { result: CheckResult }) {
  if (result.claims.length === 0) {
    return <p className="glass rounded-2xl p-5">{strings.check.noClaims}</p>;
  }
  return (
    <div className="flex flex-col gap-8">
      {result.cached_from && (
        <p className="text-muted-foreground text-sm">{strings.check.cached}</p>
      )}
      {result.claims.map((c, n) => (
        <article
          key={c.index}
          data-verdict={c.verdict.label}
          className="glass rise relative flex flex-col gap-5 overflow-hidden rounded-3xl p-6 shadow-(--shadow-lift) sm:p-8"
          style={{ "--i": n } as React.CSSProperties}
          aria-label={c.claim.quote}
        >
          <div
            aria-hidden
            className="absolute inset-x-0 top-0 h-1.5"
            style={{ background: "var(--v)" }}
          />
          <blockquote
            className="border-s-4 ps-4 text-xl leading-8 font-medium text-balance"
            style={{ borderColor: "var(--v)" }}
          >
            {c.claim.quote}
          </blockquote>
          <div>
            <VerdictBadge label={c.verdict.label} large />
          </div>
          <p className="text-muted-foreground">{c.verdict.reason}</p>
          <section
            aria-labelledby={`why-${c.index}`}
            className="bg-muted/60 rounded-2xl p-5"
          >
            <h2
              id={`why-${c.index}`}
              className="text-muted-foreground mb-2 text-xs font-semibold tracking-widest uppercase"
            >
              {strings.check.explanationHeading}
            </h2>
            <p className="leading-7">{c.explanation}</p>
          </section>
          <Receipt claim={c} versions={result.versions} />
        </article>
      ))}
    </div>
  );
}
