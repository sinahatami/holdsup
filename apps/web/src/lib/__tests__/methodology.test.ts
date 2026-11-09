import { describe, expect, it } from "vitest";
import { allowsNoGap, gapTerms, percentText } from "@/lib/methodology";
import { tolerances } from "@/test/fixtures";

describe("percentText", () => {
  it("writes a share as a percentage without floating point noise", () => {
    expect(percentText(0.05)).toBe("5%");
    expect(percentText(0.07)).toBe("7%"); // 0.07 * 100 is 7.000000000000001
    expect(percentText(0.125)).toBe("12.5%");
    expect(percentText(0.5)).toBe("50%");
  });
});

describe("gapTerms", () => {
  it("keeps only the parts a rule uses", () => {
    expect(gapTerms(tolerances.values.level)).toEqual({
      relative: null,
      absolute: null,
      rounding: true,
      plus: "1%",
    });
    expect(gapTerms(tolerances.values.percentage_points)).toEqual({
      relative: null,
      absolute: 0.5,
      rounding: true,
      plus: null,
    });
    expect(gapTerms(tolerances.values.ratio)).toEqual({
      relative: "5%",
      absolute: null,
      rounding: false,
      plus: null,
    });
  });

  it("knows when a rule allows no gap", () => {
    expect(allowsNoGap(gapTerms(tolerances.values.rank))).toBe(true);
    expect(allowsNoGap(gapTerms(tolerances.values.ratio))).toBe(false);
    expect(allowsNoGap(gapTerms(tolerances.values.level))).toBe(false);
  });
});
