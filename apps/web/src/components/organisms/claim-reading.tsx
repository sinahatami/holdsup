import { FieldList } from "@/components/molecules/field-list";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import type { ClaimSpec } from "@/lib/api/client";
import { claimReading } from "@/lib/receipt";
import { strings } from "@/lib/strings";

/** What HoldsUp took the claim to say: its statistic, place, period and figures. */
export function ClaimReading({ id, spec }: { id: string; spec: ClaimSpec }) {
  return (
    <ReceiptSection id={id} title={strings.receipt.reading.heading}>
      <FieldList
        fields={claimReading(spec).map((row) => ({
          label: row.label,
          value: row.note ? (
            <>
              {row.value}
              <span className="text-muted-foreground"> · {row.note}</span>
            </>
          ) : (
            row.value
          ),
        }))}
      />
    </ReceiptSection>
  );
}
