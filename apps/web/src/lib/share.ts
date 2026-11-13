import type { CheckResult } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { sourceName } from "@/lib/format";
import { verdictLine } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";

/**
 * What to say when a check is copied or shared, without its link: the claim and
 * how it came out, with the source for a single claim, or each claim with its own
 * verdict when there are several. The link is added where it is known, in the
 * browser, so the text never carries an address that is not the page's own.
 */
export function shareText(result: CheckResult): string {
  const t = strings.share;
  const [only, ...more] = result.claims;
  if (!only) return "";
  if (more.length === 0) {
    return t.one(
      only.claim.quote,
      strings.verdicts[shownLabel(only)],
      only.data ? sourceName(only.data.source) : null,
    );
  }
  const labels = result.claims.map((c) => ({ label: shownLabel(c) }));
  return [
    t.many(result.claims.length, verdictLine(labels)),
    ...result.claims.map((c, i) =>
      t.item(i + 1, c.claim.quote, strings.verdicts[shownLabel(c)]),
    ),
  ].join("\n");
}

/** The text plus the link: what "Copy summary" puts on the clipboard. */
export function shareSummary(text: string, url: string): string {
  return `${text}\n${url}`;
}
