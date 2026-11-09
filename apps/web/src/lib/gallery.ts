import type { GalleryClaim } from "@/lib/api/client";

/** Verdicts that say the claim stands (with or without a caveat about framing). */
const HOLDS: ReadonlySet<GalleryClaim["label"]> = new Set([
  "supported",
  "supported_framing_matters",
]);

/** How many of a check's claims hold up, for "1 of 2 claims hold up". */
export function countHolding(claims: readonly GalleryClaim[]): {
  holds: number;
  total: number;
} {
  return {
    holds: claims.filter((c) => HOLDS.has(c.label)).length,
    total: claims.length,
  };
}
