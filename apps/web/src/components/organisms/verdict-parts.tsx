import { PartRow } from "@/components/molecules/part-row";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import type { ClaimResult } from "@/lib/api/client";
import { comparison } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.receipt.compared;

/** The figures the verdict compared, one piece of the claim at a time, and the gap each allowed. */
export function VerdictParts({
  id,
  claim,
}: {
  id: string;
  claim: ClaimResult;
}) {
  const parts = comparison(claim);
  if (parts.length === 0) return null;
  return (
    <ReceiptSection id={id} title={t.heading}>
      <p className="text-muted-foreground text-sm">{t.intro}</p>
      <ul className="flex flex-col gap-3">
        {parts.map((part, i) => (
          <PartRow key={i} part={part} />
        ))}
      </ul>
    </ReceiptSection>
  );
}
