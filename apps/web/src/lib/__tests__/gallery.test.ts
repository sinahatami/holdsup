import { describe, expect, it } from "vitest";
import type { GalleryClaim } from "@/lib/api/client";
import { countHolding } from "@/lib/gallery";

const claim = (label: GalleryClaim["label"]): GalleryClaim => ({
  quote: "q",
  label,
});

describe("countHolding", () => {
  it("counts claims that hold up, with or without a framing caveat", () => {
    expect(
      countHolding([
        claim("supported"),
        claim("supported_framing_matters"),
        claim("not_supported"),
        claim("partly_supported"),
        claim("cant_check"),
      ]),
    ).toEqual({ holds: 2, total: 5 });
  });
  it("is zero of zero without claims", () => {
    expect(countHolding([])).toEqual({ holds: 0, total: 0 });
  });
});
