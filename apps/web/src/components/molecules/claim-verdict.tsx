import { ChevronDown, Gauge } from "lucide-react";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { ClaimResult } from "@/lib/api/client";
import { abstains } from "@/lib/confidence";
import { strings } from "@/lib/strings";

/**
 * A claim's verdict with how sure the check is of it (P4.5). When the check is too unsure it
 * says "Can't check confidently" and why, then what the numbers alone say, so the rules'
 * verdict is still there to read.
 */
export function ClaimVerdict({
  claim: c,
}: {
  claim: Pick<ClaimResult, "verdict" | "confidence">;
}) {
  const t = strings.confidence;
  if (abstains(c)) {
    return (
      <div className="flex flex-col gap-3">
        <div>
          <VerdictBadge label="cant_check" text={t.abstained} large />
        </div>
        {c.confidence?.reason && <p>{c.confidence.reason}</p>}
        <p className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
          {t.numbersAlone} <VerdictBadge label={c.verdict.label} />
        </p>
      </div>
    );
  }
  const level = c.confidence?.label;
  return (
    <div className="flex flex-wrap items-start gap-3">
      <VerdictBadge label={c.verdict.label} large />
      {level && (
        <details className="group text-sm">
          <summary className="text-muted-foreground hover:text-foreground inline-flex cursor-pointer list-none items-center gap-1.5 rounded-full border px-3 py-1.5 font-medium [&::-webkit-details-marker]:hidden">
            <Gauge className="size-4" aria-hidden />
            {t.label[level]}
            <ChevronDown
              className="size-4 transition group-open:rotate-180"
              aria-hidden
            />
          </summary>
          <p className="text-muted-foreground mt-2 max-w-prose leading-6">
            {t.help}
          </p>
        </details>
      )}
    </div>
  );
}
