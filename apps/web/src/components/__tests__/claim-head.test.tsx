import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarginNotes } from "@/components/molecules/margin-notes";
import { ClaimDenominator } from "@/components/organisms/claim-denominator";
import type { ClaimResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { holdingClaim, unmatchedClaim } from "@/test/fixtures";

const t = strings.claim.denominator;

describe("MarginNotes", () => {
  it("writes each note in pen, hidden from screen readers (the receipt says it in words)", () => {
    const { container } = render(<MarginNotes notes={["2015: 12.02%."]} />);
    const list = container.querySelector("ul");
    expect(list).toHaveAttribute("aria-hidden");
    expect(list).toHaveClass("pen");
    expect(list).toHaveTextContent("2015: 12.02%.");
  });

  it("draws nothing without notes", () => {
    const { container } = render(<MarginNotes notes={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ClaimDenominator", () => {
  it("sets the claim's figures beside the official ones, with where they are for and the source", () => {
    render(<ClaimDenominator claim={holdingClaim} />);
    const section = screen.getByRole("region", { name: t.heading });
    const terms = within(section).getAllByRole("term");
    expect(terms.map((dt) => dt.textContent)).toEqual([t.claimed, t.official]);
    // The arrow is drawn; a screen reader hears "to" in its place.
    expect(section).toHaveTextContent("11.9% → to 7.7%");
    expect(section).toHaveTextContent("12.02% → to 7.68%");
    expect(section).toHaveTextContent("Italy · 2015 to 2023");
    expect(section).toHaveTextContent(t.stated);
  });

  it("says in words what the claim leaves out, beside the pen's question", () => {
    const vague: ClaimResult = {
      ...holdingClaim,
      claim: { ...holdingClaim.claim, geo_basis: "inferred" },
    };
    render(<ClaimDenominator claim={vague} />);
    expect(
      screen.getByText(t.unstated(t.unstatedNames.place)),
    ).toBeInTheDocument();
  });

  it("is left out for a claim with no figure", () => {
    const { container } = render(<ClaimDenominator claim={unmatchedClaim} />);
    expect(container).toBeEmptyDOMElement();
  });
});
