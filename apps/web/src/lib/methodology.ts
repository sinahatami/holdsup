import type { ValueTolerance } from "@/lib/api/client";

/** A share as a percentage, without floating point noise: 0.07 is "7%", not "7.000000000000001%". */
export function percentText(share: number): string {
  return `${Number((share * 100).toFixed(2))}%`;
}

/**
 * The parts of an allowed gap, as the API's rule is built: a figure may be off by the
 * largest of a share of the claimed figure, a fixed amount, and half a unit of its last
 * written digit, plus a further share for later revisions of the data. Only the parts the
 * rule uses are set.
 */
export interface GapTerms {
  relative: string | null;
  absolute: number | null;
  rounding: boolean;
  plus: string | null;
}

export function gapTerms(t: ValueTolerance): GapTerms {
  return {
    relative: t.relative > 0 ? percentText(t.relative) : null,
    absolute: t.absolute > 0 ? t.absolute : null,
    rounding: t.rounding,
    plus: t.plus_relative > 0 ? percentText(t.plus_relative) : null,
  };
}

/** True when the rule allows no gap at all (a position in a ranking). */
export function allowsNoGap(terms: GapTerms): boolean {
  return (
    terms.relative === null &&
    terms.absolute === null &&
    !terms.rounding &&
    terms.plus === null
  );
}
