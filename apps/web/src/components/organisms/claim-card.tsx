import Link from "next/link";
import type { CSSProperties } from "react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { Receipt } from "@/components/organisms/receipt";
import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

type Models = NonNullable<CheckResult["models"]>;

/** When nothing matched: the nearest statistics, and the way to the whole list. */
function Suggestions({ claim: c }: { claim: ClaimResult }) {
  const near = c.suggestions ?? [];
  if (c.verdict.label !== "cant_check" || c.retryable) return null;
  return (
    <section className="flex flex-col gap-2 text-sm">
      {near.length > 0 && (
        <>
          <Eyebrow as="h3">{strings.check.closestHeading}</Eyebrow>
          <ul className="list-disc ps-5">
            {near.map((s) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
        </>
      )}
      <Link
        href={routes.indicators}
        className="text-brand w-fit font-medium underline underline-offset-4"
      >
        {strings.check.seeAll}
      </Link>
    </section>
  );
}

/** One checked claim: the quote, the verdict, why, and the receipt. */
export function ClaimCard({
  claim: c,
  versions,
  sharedModels,
  order,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
  sharedModels?: Models;
  /** Position in the list; staggers the entrance animation. */
  order: number;
}) {
  const whyId = `why-${c.index}`;
  return (
    <article
      data-verdict={c.verdict.label}
      className="glass rise relative flex flex-col gap-5 overflow-hidden rounded-3xl p-6 shadow-(--shadow-lift) sm:p-8"
      style={{ "--i": order } as CSSProperties}
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
      {c.claim.speaker && <NeutralityNote />}
      <p className="text-muted-foreground">{c.verdict.reason}</p>
      {c.explanation && (
        <section
          aria-labelledby={whyId}
          className="bg-muted/60 rounded-2xl p-5"
        >
          <Eyebrow id={whyId} className="mb-2">
            {strings.check.explanationHeading}
          </Eyebrow>
          <p className="leading-7">{c.explanation}</p>
        </section>
      )}
      <Suggestions claim={c} />
      <Receipt claim={c} versions={versions} sharedModels={sharedModels} />
    </article>
  );
}
