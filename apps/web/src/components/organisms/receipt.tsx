import { SectionTitle } from "@/components/atoms/section-title";
import { ClaimReading } from "@/components/organisms/claim-reading";
import { Recomputation } from "@/components/organisms/recomputation";
import { SeriesDetails } from "@/components/organisms/series-details";
import { TechnicalDetails } from "@/components/organisms/technical-details";
import { VerdictParts } from "@/components/organisms/verdict-parts";
import { VerifyYourself } from "@/components/organisms/verify-yourself";
import type { ClaimResult, CheckResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.receipt;

/**
 * The receipt of one claim, open on the page: how the claim was read, the
 * official series it was matched to, every calculation, what the verdict
 * compared, and how to check it again (or run its notebook). The technical
 * details fold away. A double rule across its top, as on a till slip.
 */
export function Receipt({
  claim,
  versions,
  sharedModels = [],
  checkId,
}: {
  claim: ClaimResult;
  versions: CheckResult["versions"];
  /** Models that served the whole check (reading the claims), not one claim. */
  sharedModels?: NonNullable<CheckResult["models"]>;
  /** The stored check, for its notebook download. */
  checkId?: string;
}) {
  const id = `receipt-${claim.index}`;
  return (
    <section
      aria-labelledby={`${id}-heading`}
      data-testid="receipt"
      className="border-foreground/70 flex flex-col gap-6 border-t-4 border-double pt-8"
    >
      <div className="flex flex-col gap-1">
        <SectionTitle id={`${id}-heading`}>{t.heading}</SectionTitle>
        <p className="text-muted-foreground">{t.intro}</p>
      </div>
      <ClaimReading id={`${id}-reading`} spec={claim.claim} />
      <SeriesDetails id={`${id}-series`} claim={claim} />
      <Recomputation id={`${id}-steps`} claim={claim} />
      <VerdictParts id={`${id}-compared`} claim={claim} />
      <VerifyYourself id={`${id}-verify`} claim={claim} checkId={checkId} />
      <TechnicalDetails
        claim={claim}
        versions={versions}
        sharedModels={sharedModels}
      />
    </section>
  );
}
