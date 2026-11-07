import type { CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { Receipt } from "@/components/receipt";
import { VerdictBadge } from "@/components/verdict";

export function CheckResultView({ result }: { result: CheckResult }) {
  if (result.claims.length === 0) {
    return <p>{strings.check.noClaims}</p>;
  }
  return (
    <div className="flex flex-col gap-8">
      {result.cached_from && (
        <p className="text-muted-foreground text-sm">{strings.check.cached}</p>
      )}
      {result.claims.map((c) => (
        <article
          key={c.index}
          className="flex flex-col gap-3"
          aria-label={c.claim.quote}
        >
          <blockquote className="border-s-4 ps-4 text-lg">
            {c.claim.quote}
          </blockquote>
          <div>
            <VerdictBadge label={c.verdict.label} />
          </div>
          <p className="text-muted-foreground text-sm">{c.verdict.reason}</p>
          <section aria-labelledby={`why-${c.index}`}>
            <h2 id={`why-${c.index}`} className="mb-1 text-lg font-semibold">
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
