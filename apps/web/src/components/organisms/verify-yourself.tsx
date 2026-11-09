import { ExternalLink } from "@/components/atoms/external-link";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import type { ClaimResult } from "@/lib/api/client";
import { formatDate, sourceName } from "@/lib/format";
import { strings } from "@/lib/strings";

const t = strings.receipt.verify;

/**
 * How a reader can redo the check without trusting HoldsUp: open the same data,
 * find the same figures, repeat the calculation and compare. It points at the
 * receipt's own steps and links rather than repeating their numbers.
 */
export function VerifyYourself({
  id,
  claim,
}: {
  id: string;
  claim: ClaimResult;
}) {
  const { data } = claim;
  if (!data) return null;
  const source = sourceName(data.source);
  const hasSteps = (claim.operations ?? []).length > 0;
  const hasParts = (claim.verdict.parts ?? []).length > 0;
  return (
    <ReceiptSection id={id} title={t.heading}>
      <ol className="flex list-decimal flex-col gap-2 ps-5 text-sm marker:font-semibold">
        <li>
          <strong>{t.open}</strong>{" "}
          <ExternalLink href={data.url}>
            {source} {data.dataset}
          </ExternalLink>
          . {t.openBody}
        </li>
        <li>
          <strong>{t.find}</strong> {t.findBody}{" "}
          {t.revised(source, formatDate(data.retrieved_at))}
        </li>
        {hasSteps && (
          <li>
            <strong>{t.repeat}</strong> {t.repeatBody}
          </li>
        )}
        {hasParts && (
          <li>
            <strong>{t.compare}</strong> {t.compareBody}
          </li>
        )}
      </ol>
    </ReceiptSection>
  );
}
