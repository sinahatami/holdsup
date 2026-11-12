import type { CSSProperties } from "react";
import { Eyebrow } from "@/components/atoms/eyebrow";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { CantCheckHelp } from "@/components/organisms/cant-check-help";
import { FramingChecks } from "@/components/organisms/framing-checks";
import { Receipt } from "@/components/organisms/receipt";
import { RecheckOptions } from "@/components/organisms/recheck-options";
import { ReportMatch } from "@/components/organisms/report-match";
import { SeriesChart } from "@/components/organisms/series-chart";
import { WindowHeatmap } from "@/components/organisms/window-heatmap";
import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { chartOf } from "@/lib/series-chart";
import { strings } from "@/lib/strings";

type Models = NonNullable<CheckResult["models"]>;

/** One checked claim: the quote, the verdict, why, the data, other time windows, the framing checks, the receipt, and other statistics to re-check with. */
export function ClaimCard({
  claim: c,
  versions,
  sharedModels,
  order,
  total,
  checkId,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
  sharedModels?: Models;
  /** Position in the list; staggers the entrance animation. */
  order: number;
  /** How many claims the check has, so each can be named "Claim 2 of 3". */
  total: number;
  /** The check this claim belongs to, which a report about it is sent against. */
  checkId: string;
}) {
  const whyId = `why-${c.index}`;
  const chart = c.verdict.label === "cant_check" ? null : chartOf(c);
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
      <h2 className="sr-only">{strings.check.claimOf(order + 1, total)}</h2>
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
          <Eyebrow as="h3" id={whyId} className="mb-2">
            {strings.check.explanationHeading}
          </Eyebrow>
          <p className="leading-7">{c.explanation}</p>
        </section>
      )}
      {chart && <SeriesChart chart={chart} />}
      {c.sweep && c.verdict.label !== "cant_check" && (
        <WindowHeatmap
          sweep={c.sweep}
          direction={c.claim.assertion.direction ?? null}
          threshold={c.verdict.framing_threshold}
          breaks={c.changepoints?.breaks ?? []}
        />
      )}
      <FramingChecks claim={c} />
      <CantCheckHelp claim={c} checkId={checkId} />
      <Receipt
        claim={c}
        versions={versions}
        sharedModels={sharedModels}
        checkId={checkId}
      />
      <RecheckOptions claim={c} checkId={checkId} />
      <ReportMatch checkId={checkId} claimIndex={c.index} />
    </article>
  );
}
