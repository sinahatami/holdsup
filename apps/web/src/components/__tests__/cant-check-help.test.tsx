import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimCard } from "@/components/organisms/claim-card";
import type { ClaimResult } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { holdingClaim, unmatchedClaim, versions } from "@/test/fixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const t = strings.cantCheck;

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

const help = () => screen.queryByRole("region", { name: t.heading });

/** A claim whose statistic was found but that stopped later. */
const found = (over: Partial<ClaimResult>): ClaimResult => ({
  ...unmatchedClaim,
  indicator: holdingClaim.indicator,
  suggestions: [],
  ...over,
});
const name = holdingClaim.indicator!.name;

describe("help under a claim that could not be checked", () => {
  it("when nothing matched: says so, gives tips, links the nearest statistics, and offers the claim to reword", () => {
    card({ ...unmatchedClaim, stopped_at: "match" });
    const box = within(help()!);
    expect(box.getByText(t.cause.no_series)).toBeInTheDocument();
    for (const tip of t.tips) expect(box.getByText(tip)).toBeInTheDocument();
    expect(
      box.getByRole("link", { name: "Total population (Eurostat)" }),
    ).toHaveAttribute(
      "href",
      routes.indicatorSearch("Total population (Eurostat)"),
    );
    expect(
      box.getByRole("link", { name: strings.check.seeAll }),
    ).toHaveAttribute("href", routes.indicators);
    const reword = box.getByRole("textbox", { name: t.rewordLabel });
    expect(reword).toHaveValue(unmatchedClaim.claim.quote);
    expect(
      box.getByRole("button", { name: strings.home.submit }),
    ).toBeEnabled();
    // It is a reword box, not the home page's: no examples to pick from.
    expect(box.queryByText(strings.home.examplesHeading)).toBeNull();
  });

  it("treats a result stored before the stopping step was recorded, with no statistic, as nothing matched", () => {
    card({ ...unmatchedClaim, stopped_at: null });
    expect(within(help()!).getByText(t.cause.no_series)).toBeInTheDocument();
  });

  it("when the source has no figures: names the statistic and links to what it covers", () => {
    card(found({ stopped_at: "fetch" }));
    const box = within(help()!);
    expect(box.getByText(t.cause.no_figures(name))).toBeInTheDocument();
    expect(box.getByRole("link", { name: t.coverage(name) })).toHaveAttribute(
      "href",
      routes.indicatorSearch(name),
    );
    // Rewording the wording will not help here, so no tips.
    expect(box.queryByText(t.tipsHeading)).toBeNull();
  });

  it.each(["plan", "execute", "verdict"] as const)(
    "when it stopped at %s: says that kind of claim cannot be recomputed yet, and where that is explained",
    (step) => {
      card(found({ stopped_at: step }));
      const box = within(help()!);
      expect(box.getByText(t.cause.unsupported(name))).toBeInTheDocument();
      expect(box.getByRole("link", { name: t.cannotLink })).toHaveAttribute(
        "href",
        routes.cannotCheck,
      );
    },
  );

  it("says only that it could not be checked when the cause is not known", () => {
    card(found({ stopped_at: null }));
    const box = within(help()!);
    expect(box.getByText(t.cause.unknown)).toBeInTheDocument();
    expect(box.queryByText(t.tipsHeading)).toBeNull();
    expect(box.getByRole("textbox")).toBeInTheDocument();
  });

  it("is not shown when a source was only briefly down: that needs trying again, not rewording", () => {
    card({ ...unmatchedClaim, retryable: true, stopped_at: "fetch" });
    expect(help()).toBeNull();
  });

  it("is not shown for a claim that was checked", () => {
    card(holdingClaim);
    expect(help()).toBeNull();
  });

  it("gives each claim's reword box its own id, so two can sit on one page", () => {
    render(
      <>
        <ClaimCard
          claim={{ ...unmatchedClaim, index: 0, stopped_at: "match" }}
          versions={versions}
          order={0}
          total={2}
          checkId="c1"
        />
        <ClaimCard
          claim={{ ...unmatchedClaim, index: 1, stopped_at: "match" }}
          versions={versions}
          order={1}
          total={2}
          checkId="c1"
        />
      </>,
    );
    const boxes = screen.getAllByRole("textbox", { name: t.rewordLabel });
    expect(boxes).toHaveLength(2);
    expect(boxes[0].id).not.toBe(boxes[1].id);
  });
});
