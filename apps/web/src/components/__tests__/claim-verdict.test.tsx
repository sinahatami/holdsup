import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimVerdict } from "@/components/molecules/claim-verdict";
import { ClaimCard } from "@/components/organisms/claim-card";
import { OriginalText } from "@/components/organisms/original-text";
import { shareText } from "@/lib/share";
import { strings } from "@/lib/strings";
import {
  checkResult,
  highConfidence,
  holdingClaim,
  unsureClaim,
  unsureReason,
  versions,
} from "@/test/fixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const t = strings.confidence;
const confident = { ...holdingClaim, confidence: highConfidence };

describe("ClaimVerdict", () => {
  it("gives a sure verdict with its confidence, explained on demand", () => {
    render(<ClaimVerdict claim={confident} />);
    expect(screen.getByText(strings.verdicts.supported)).toBeInTheDocument();
    const level = screen.getByText(t.label.high);
    expect(screen.getByText(t.help)).not.toBeVisible();
    fireEvent.click(level);
    expect(screen.getByText(t.help)).toBeVisible();
    expect(screen.queryByText(t.abstained)).not.toBeInTheDocument();
  });

  it("withholds an unsure verdict, says why, and still shows what the numbers say", () => {
    render(<ClaimVerdict claim={unsureClaim} />);
    expect(screen.getByText(t.abstained)).toBeInTheDocument();
    expect(screen.getByText(unsureReason)).toBeInTheDocument();
    const alone = screen.getByText(t.numbersAlone);
    expect(
      within(alone).getByText(strings.verdicts.supported),
    ).toBeInTheDocument();
    expect(screen.queryByText(t.label.low)).not.toBeInTheDocument();
  });

  it("shows the verdict alone when no confidence model scored it", () => {
    render(<ClaimVerdict claim={holdingClaim} />);
    expect(screen.getByText(strings.verdicts.supported)).toBeInTheDocument();
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });
});

describe("an abstained claim elsewhere on the page", () => {
  it("is coloured and shared as can't check", () => {
    const { container } = render(
      <ClaimCard
        claim={unsureClaim}
        versions={versions}
        order={0}
        total={1}
        checkId="c1"
      />,
    );
    expect(container.querySelector("article")).toHaveAttribute(
      "data-verdict",
      "cant_check",
    );
    const result = checkResult([confident, unsureClaim]);
    expect(shareText(result)).toContain(
      `2. “${unsureClaim.claim.quote}” — ${strings.verdicts.cant_check}`,
    );
  });

  it("is marked as can't check in the original text", () => {
    const { container } = render(
      <OriginalText result={checkResult([unsureClaim])} />,
    );
    expect(container.querySelector("mark")).toHaveAttribute(
      "data-verdict",
      "cant_check",
    );
  });
});
