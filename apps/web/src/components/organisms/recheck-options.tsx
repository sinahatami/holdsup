import { Eyebrow } from "@/components/atoms/eyebrow";
import { RecheckList } from "@/components/molecules/recheck-list";
import type { ClaimResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.recheck;

/**
 * Under a checked claim: the other statistics it could be about, each one click from a
 * re-check. A claim that could not be checked offers its closest statistics in its own
 * help instead.
 */
export function RecheckOptions({
  claim: c,
  checkId,
}: {
  claim: ClaimResult;
  checkId: string;
}) {
  const statistics = c.suggestions ?? [];
  if (statistics.length === 0 || c.verdict.label === "cant_check") return null;
  const headingId = `recheck-${c.index}`;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <Eyebrow as="h3" id={headingId}>
        {t.heading}
      </Eyebrow>
      <p className="text-muted-foreground text-sm leading-6">{t.intro}</p>
      <RecheckList
        checkId={checkId}
        claimIndex={c.index}
        quote={c.claim.quote}
        statistics={statistics}
      />
    </section>
  );
}
