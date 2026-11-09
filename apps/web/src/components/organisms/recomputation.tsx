import { Fragment } from "react";
import { ExternalLink } from "@/components/atoms/external-link";
import { OperationItem } from "@/components/molecules/operation-item";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import type { ClaimResult } from "@/lib/api/client";
import { sourceLinks } from "@/lib/receipt";
import { strings } from "@/lib/strings";

const t = strings.receipt.recompute;

/** Every calculation HoldsUp ran, in order, with the figures it used and what each gave. */
export function Recomputation({
  id,
  claim,
}: {
  id: string;
  claim: ClaimResult;
}) {
  const operations = claim.operations ?? [];
  if (operations.length === 0) return null;
  const decides = new Set(claim.answer ?? []);
  const links = sourceLinks(claim);
  return (
    <ReceiptSection id={id} title={t.heading}>
      {links.length > 0 && (
        <p className="text-sm">
          {t.valuesFrom}{" "}
          {links.map((link, i) => (
            <Fragment key={link.url}>
              {i > 0 && ", "}
              <ExternalLink href={link.url}>{link.label}</ExternalLink>
            </Fragment>
          ))}
          .
        </p>
      )}
      <ol className="flex flex-col gap-3">
        {operations.map((op, i) => (
          <OperationItem
            key={i}
            op={op}
            step={i + 1}
            decides={decides.has(i)}
          />
        ))}
      </ol>
    </ReceiptSection>
  );
}
