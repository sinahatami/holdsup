import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ClaimDenominator } from "@/components/organisms/claim-denominator";
import { holdingClaim } from "@/test/fixtures";

const words = "deaths per 1,000 live births";

function withWords() {
  const { indicator } = holdingClaim;
  if (!indicator) throw new Error("the fixture is matched");
  return { ...holdingClaim, indicator: { ...indicator, unit: words } };
}

/** The large figures of each side, as a screen reader reads them ("11.9 to 7.7"). */
const figures = (container: HTMLElement) =>
  [...container.querySelectorAll("dd > span:first-child")].map((s) =>
    s.textContent
      ?.replace(/\s*→\s*/g, " ")
      .replace(/\s+/g, " ")
      .trim(),
  );

describe("ClaimDenominator", () => {
  it("keeps a unit in words out of the large figures and says it once under each side", () => {
    const { container } = render(<ClaimDenominator claim={withWords()} />);
    expect(figures(container)).toEqual(["11.9 to 7.7", "12.02 to 7.68"]);
    expect(screen.getAllByText(words)).toHaveLength(2);
  });

  it("leaves a sign such as % on the numbers, with no caption", () => {
    const { container } = render(<ClaimDenominator claim={holdingClaim} />);
    expect(figures(container)).toEqual(["11.9% to 7.7%", "12.02% to 7.68%"]);
    expect(screen.queryByText(words)).toBeNull();
  });
});
