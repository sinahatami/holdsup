import type { ClaimResult, Label } from "@/lib/api/client";

type Judged = Pick<ClaimResult, "verdict" | "confidence">;

/** Whether the check is too unsure of a claim's verdict to give it as the answer (P4.5). */
export function abstains(c: Pick<ClaimResult, "confidence">): boolean {
  return c.confidence?.abstain === true;
}

/**
 * The verdict a reader is given: "Can't check" when the check abstains. The rules' own
 * verdict stays on the claim card and the receipt, as what the numbers alone say.
 */
export function shownLabel(c: Judged): Label {
  return abstains(c) ? "cant_check" : c.verdict.label;
}
