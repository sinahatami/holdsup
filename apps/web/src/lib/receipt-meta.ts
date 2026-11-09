import type { CheckResult, Label } from "@/lib/api/client";
import { countHolding } from "@/lib/gallery";
import { strings } from "@/lib/strings";

const TITLE_CLAIM_MAX = 90;
const DESCRIPTION_MAX = 200;

/** One line of text: whitespace collapsed, cut at `max` characters with an ellipsis. */
export function clip(text: string, max: number): string {
  const line = text.replace(/\s+/g, " ").trim();
  return line.length <= max ? line : `${line.slice(0, max - 1).trimEnd()}…`;
}

/** How a check came out in a few words: one verdict, or "1 of 2 claims hold up". */
export function verdictLine(claims: readonly { label: Label }[]): string {
  if (claims.length === 1) return strings.verdicts[claims[0].label];
  const { holds, total } = countHolding(claims);
  return strings.home.card.summary(holds, total);
}

const labels = (result: CheckResult) =>
  result.claims.map((c) => ({ label: c.verdict.label }));

/** The page title and the shared link's title: the outcome, then the claim. */
export function receiptTitle(result: CheckResult): string {
  const claim =
    result.claims.length === 1 ? result.claims[0].claim.quote : result.text;
  return strings.check.metaTitle(
    verdictLine(labels(result)),
    clip(claim, TITLE_CLAIM_MAX),
  );
}

/**
 * The short text under the title: why a single claim came out as it did (the
 * explanation shown on the page), or the text that was checked when there are
 * several claims.
 */
export function receiptDescription(result: CheckResult): string {
  const only = result.claims.length === 1 ? result.claims[0] : null;
  return clip(
    only ? only.explanation || only.verdict.reason : result.text,
    DESCRIPTION_MAX,
  );
}
