import type { CheckResult, ClaimResult } from "@/lib/api/client";
import { checkResult, holdingClaim } from "@/test/fixtures";

/** The check of holdingClaim the claim watch made after Eurostat revised 2023 (S1). */
export const EARLIER_ID = "22222222-2222-4222-8222-222222222222";

export const revisedClaim: ClaimResult = {
  ...holdingClaim,
  verdict: { ...holdingClaim.verdict, label: "partly_supported" },
  explanation_source: "template",
};

export function updateResult(
  claims: ClaimResult[] = [revisedClaim],
  over: Partial<CheckResult> = {},
): CheckResult {
  return checkResult(claims, {
    id: "33333333-3333-4333-8333-333333333333",
    created_at: "2026-12-07T06:29:00Z",
    finished_at: "2026-12-07T06:29:00Z",
    update_of: {
      check_id: EARLIER_ID,
      created_at: "2026-11-07T10:00:00Z",
      checked_on: "2026-11-07",
      changes: [
        {
          index: 0,
          before: "supported",
          after: "partly_supported",
          figures: [
            { name: "assertion", period: null, before: -4.34, after: -2.84 },
            { name: "end value", period: "2023", before: 7.68, after: 9.18 },
          ],
        },
      ],
    },
    ...over,
  });
}
