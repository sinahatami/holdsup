import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BrandCard, ReceiptCard } from "@/app/check/[id]/og-card";
import { strings } from "@/lib/strings";
import {
  checkResult,
  holdingClaim,
  partlyClaim,
  unmatchedClaim,
} from "@/test/fixtures";

describe("ReceiptCard", () => {
  it("shows the claim, the verdict, the figure beside the official one, and the source", () => {
    render(<ReceiptCard result={checkResult([holdingClaim])} />);
    expect(
      screen.getByText(`“${holdingClaim.claim.quote}”`),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.verdicts.supported)).toBeInTheDocument();
    expect(screen.getByText(strings.og.claimed).nextSibling).toHaveTextContent(
      "7.7%",
    );
    expect(screen.getByText(strings.og.official).nextSibling).toHaveTextContent(
      "7.68%",
    );
    expect(screen.getByText("Checked against Eurostat")).toBeInTheDocument();
    expect(screen.getByText(strings.appName)).toBeInTheDocument();
  });

  it("states the claim's own figure when it has one", () => {
    render(<ReceiptCard result={checkResult([partlyClaim])} />);
    expect(
      screen.getByText(strings.verdicts.partly_supported),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.og.claimed).nextSibling).toHaveTextContent(
      "-12 points",
    );
    expect(screen.getByText(strings.og.official).nextSibling).toHaveTextContent(
      "-10.7 points",
    );
  });

  it("sets longer figures smaller, so that both fit side by side", () => {
    const sizeOf = (result: ReturnType<typeof checkResult>) => {
      const { unmount } = render(<ReceiptCard result={result} />);
      const value = screen.getByText(strings.og.official).nextSibling;
      const size = (value as HTMLElement).style.fontSize;
      unmount();
      return size;
    };
    // "7.7%" beside "7.68%" against "-12 points" beside "-10.7 points".
    expect(sizeOf(checkResult([holdingClaim]))).toBe("60px");
    expect(sizeOf(checkResult([partlyClaim]))).toBe("48px");
  });

  it("has no figures or source for a claim that could not be checked", () => {
    render(<ReceiptCard result={checkResult([unmatchedClaim])} />);
    expect(screen.getByText(strings.verdicts.cant_check)).toBeInTheDocument();
    expect(screen.queryByText(strings.og.claimed)).not.toBeInTheDocument();
    expect(screen.queryByText(/Checked against/)).not.toBeInTheDocument();
  });

  it("counts the claims that hold up, and shows the whole text, when there are several", () => {
    const text = "First claim 5%. Second claim 6%.";
    render(
      <ReceiptCard
        result={checkResult([holdingClaim, { ...partlyClaim, index: 1 }], {
          text,
        })}
      />,
    );
    expect(screen.getByText("1 of 2 claims hold up")).toBeInTheDocument();
    expect(screen.getByText(`“${text}”`)).toBeInTheDocument();
    expect(screen.queryByText(strings.og.claimed)).not.toBeInTheDocument();
  });

  it("cuts a long text to fit the picture", () => {
    const long = "word ".repeat(100);
    render(
      <ReceiptCard
        result={checkResult([
          { ...holdingClaim, claim: { ...holdingClaim.claim, quote: long } },
        ])}
      />,
    );
    const shown = screen.getByText(/^“word/).textContent ?? "";
    expect(shown.length).toBeLessThanOrEqual(204);
    expect(shown).toMatch(/…”$/);
  });
});

describe("BrandCard", () => {
  it("shows the name, the tagline and what the site does", () => {
    render(<BrandCard />);
    expect(screen.getByText(strings.appName)).toBeInTheDocument();
    expect(screen.getByText(strings.tagline)).toBeInTheDocument();
    expect(screen.getByText(strings.metaDescription)).toBeInTheDocument();
  });
});
