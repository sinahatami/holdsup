import { Download } from "lucide-react";
import { ExternalLink } from "@/components/atoms/external-link";
import { ReceiptSection } from "@/components/molecules/receipt-section";
import { notebookUrl, type ClaimResult } from "@/lib/api/client";
import { formatDate, sourceName } from "@/lib/format";
import { strings } from "@/lib/strings";

const t = strings.receipt.verify;

/**
 * How a reader can redo the check without trusting HoldsUp: open the same data,
 * find the same figures, repeat the calculation and compare. It points at the
 * receipt's own steps and links rather than repeating their numbers. A stored check
 * also offers the notebook that repeats every calculation.
 */
export function VerifyYourself({
  id,
  claim,
  checkId,
}: {
  id: string;
  claim: ClaimResult;
  /** The stored check, for its notebook; none for a receipt shown on its own. */
  checkId?: string;
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
        {hasSteps && checkId && (
          <li>
            <strong>{t.notebook}</strong> {t.notebookBody}{" "}
            <a
              href={notebookUrl(checkId)}
              download
              className="text-brand inline-flex items-center gap-1 font-medium underline underline-offset-4"
            >
              <Download className="size-3.5" aria-hidden />
              {t.notebookLink}
            </a>
          </li>
        )}
      </ol>
    </ReceiptSection>
  );
}
