import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimCard } from "@/components/organisms/claim-card";
import type { ClaimResult, DistortionCheck } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { holdingClaim, unmatchedClaim, versions } from "@/test/fixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const t = strings.framing;

const card = (claim: ClaimResult) =>
  render(
    <ClaimCard
      claim={claim}
      versions={versions}
      order={0}
      total={1}
      checkId="c1"
    />,
  );

const section = () => screen.queryByRole("region", { name: t.heading });

// What the API gives a pay rise below inflation (tests/pipeline/test_framing_checks.py).
const real: DistortionCheck = {
  kind: "real",
  flagged: true,
  text: "after inflation it fell: 30,000 in 2015, 27,172 in 2020 (euro per year, 2015 prices)",
  records: [],
  uses: "cpi_inflation_annual",
};

describe("FramingChecks", () => {
  it("lists each check with its result in words and the line the code wrote", () => {
    card(holdingClaim);
    const list = within(section()!).getAllByRole("listitem");
    expect(list).toHaveLength(1);
    expect(list[0]).toHaveTextContent(t.kinds.endpoints);
    expect(list[0]).toHaveTextContent(t.passed);
    // A clause from the API, shown as a sentence.
    expect(list[0]).toHaveTextContent(
      "Neither the start (2015) nor the end (2023) is at a peak, a trough or a turn in the trend that carries the claim.",
    );
  });

  it("puts a flagged check first and names it", () => {
    card({
      ...holdingClaim,
      verdict: { ...holdingClaim.verdict, label: "supported_framing_matters" },
      distortion_checks: [...(holdingClaim.distortion_checks ?? []), real],
    });
    const [first, second] = within(section()!).getAllByRole("listitem");
    expect(first).toHaveTextContent(t.kinds.real);
    expect(first).toHaveTextContent(t.flagged);
    expect(first).toHaveTextContent(
      "After inflation it fell: 30,000 in 2015, 27,172 in 2020 (euro per year, 2015 prices).",
    );
    expect(
      within(first!).getByText(t.flagged).closest("[data-verdict]"),
    ).toHaveAttribute("data-verdict", "supported_framing_matters");
    expect(second).toHaveTextContent(t.passed);
  });

  it("is left out when no check applied or the claim can't be checked", () => {
    card({ ...holdingClaim, distortion_checks: [] });
    expect(section()).toBeNull();
  });

  it("is left out of a claim that can't be checked", () => {
    card({ ...unmatchedClaim, distortion_checks: [real] });
    expect(section()).toBeNull();
  });
});
