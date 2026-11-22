import type { CSSProperties } from "react";
import { MarkedQuote } from "@/components/atoms/marked-quote";
import { SectionTitle } from "@/components/atoms/section-title";
import { ClaimVerdict } from "@/components/molecules/claim-verdict";
import { MarginNotes } from "@/components/molecules/margin-notes";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { CantCheckHelp } from "@/components/organisms/cant-check-help";
import { ClaimDenominator } from "@/components/organisms/claim-denominator";
import { FramingChecks } from "@/components/organisms/framing-checks";
import { Receipt } from "@/components/organisms/receipt";
import { RecheckOptions } from "@/components/organisms/recheck-options";
import { ReportMatch } from "@/components/organisms/report-match";
import { SeriesChart } from "@/components/organisms/series-chart";
import { WindowHeatmap } from "@/components/organisms/window-heatmap";
import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { marginNotes } from "@/lib/receipt";
import { chartOf } from "@/lib/series-chart";
import { strings } from "@/lib/strings";

type Models = NonNullable<CheckResult["models"]>;

/**
 * One checked claim, as an edited sheet: the quote with its verdict stamped on it and the
 * editor's notes in the margin, the claim over its denominator, why, the data, other time
 * windows, the framing checks, the receipt, and other statistics to re-check with.
 */
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
  const heatmap = c.verdict.label === "cant_check" ? null : c.sweep;
  return (
    <article
      data-verdict={shownLabel(c)}
      className="glass rise relative flex flex-col gap-10 p-6 shadow-(--shadow-lift) sm:p-10"
      style={{ "--i": order } as CSSProperties}
      aria-label={c.claim.quote}
    >
      <h2 className="sr-only">{strings.check.claimOf(order + 1, total)}</h2>
      {/* The sheet, then its margin: beside it from lg up, under it on a phone. */}
      <div className="grid gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,1fr)_14rem]">
        <div className="flex flex-col gap-5">
          <blockquote className="font-heading text-[1.875rem] leading-[1.3] text-balance sm:text-[2.375rem]">
            <MarkedQuote text={c.claim.quote} />
          </blockquote>
          <ClaimVerdict claim={c} />
          {c.claim.speaker && <NeutralityNote />}
          <p className="text-muted-foreground">{c.verdict.reason}</p>
        </div>
        <MarginNotes notes={marginNotes(c)} />
      </div>
      <ClaimDenominator claim={c} />
      {c.explanation && (
        <section aria-labelledby={whyId} className="flex flex-col gap-2">
          <SectionTitle id={whyId}>
            {strings.check.explanationHeading}
          </SectionTitle>
          <p className="max-w-prose text-lg leading-8">{c.explanation}</p>
        </section>
      )}
      {/* The data and the receipt start below the fold on a phone, so they are laid out
          once scrolled near (.defer-render). -m-2 p-2 gives focus rings on their edges
          room to draw, and leaves the layout as it was. */}
      {(chart || heatmap) && (
        <div className="defer-render -m-2 flex flex-col gap-10 p-2">
          {chart && <SeriesChart chart={chart} />}
          {heatmap && (
            <WindowHeatmap
              sweep={heatmap}
              direction={c.claim.assertion.direction ?? null}
              threshold={c.verdict.framing_threshold}
              breaks={c.changepoints?.breaks ?? []}
            />
          )}
        </div>
      )}
      <div className="defer-render -m-2 flex flex-col gap-10 p-2">
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
      </div>
    </article>
  );
}
