import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CheckResultView } from "@/components/organisms/check-result";
import { Receipt } from "@/components/organisms/receipt";
import type { ClaimResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";
import {
  checkResult,
  holdingClaim,
  partlyClaim,
  unmatchedClaim,
  versions,
} from "@/test/fixtures";

const t = strings.receipt;

const open = (
  claim: ClaimResult,
  props: Partial<Parameters<typeof Receipt>[0]> = {},
) => render(<Receipt claim={claim} versions={versions} {...props} />);

/** A section of the receipt, found by its heading. */
const section = (name: string) => within(screen.getByRole("region", { name }));

describe("Receipt", () => {
  it("runs from how the claim was read to how to verify it, then folds the technical details", () => {
    open(holdingClaim);
    expect(
      screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent),
    ).toEqual([
      t.reading.heading,
      t.series.heading,
      t.recompute.heading,
      t.compared.heading,
      t.verify.heading,
    ]);
    const details = screen.getByText(t.technical.heading).closest("details");
    expect(details).not.toHaveAttribute("open");
  });

  it("is a region named Receipt, open on the page", () => {
    open(holdingClaim);
    const receipt = screen.getByRole("region", { name: t.heading });
    expect(receipt).toBeVisible();
    expect(within(receipt).getByText(t.intro)).toBeInTheDocument();
  });

  it("says how the claim was read, in words", () => {
    open(partlyClaim);
    const reading = section(t.reading.heading);
    expect(reading.getByText("Italy")).toBeInTheDocument();
    expect(reading.getByText(/inferred from the context/)).toBeInTheDocument();
    expect(
      reading.getByText(/February 2014 to the latest period/),
    ).toBeInTheDocument();
    expect(reading.getByText("Renzi, 2018")).toBeInTheDocument();
  });

  it("names the series, where its data is, and when it was updated and fetched", () => {
    open(holdingClaim);
    const series = section(t.series.heading);
    expect(series.getByText("Unemployment rate (monthly)")).toBeInTheDocument();
    expect(series.getByText("Eurostat")).toBeInTheDocument();
    expect(
      series.getByText("une_rt_m: Unemployment by sex and age - monthly data"),
    ).toBeInTheDocument();
    const link = series.getByRole("link", { name: /Open the data/ });
    expect(link).toHaveAttribute("href", holdingClaim.data?.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(series.getByText("November 5, 2026, 22:00 UTC")).toBeInTheDocument();
    expect(series.getByText("November 7, 2026, 16:45 UTC")).toBeInTheDocument();
    expect(series.getByText("Eurostat (une_rt_m)")).toBeInTheDocument();
    expect(
      series.getByText(
        "Matches the exact definition: the monthly unemployment rate.",
      ),
    ).toBeInTheDocument();
  });

  it("lists each calculation in words, with its call, figures and result", () => {
    open(holdingClaim);
    const steps = section(t.recompute.heading);
    expect(steps.getByText("Step 1")).toBeInTheDocument();
    expect(steps.getByText(t.recompute.decides)).toBeInTheDocument();
    expect(
      steps.getByText("Take the rate for 2015 away from the rate for 2023."),
    ).toBeInTheDocument();
    expect(steps.getByText(/change\(/)).toBeInTheDocument();
    expect(
      steps.getByText("Italy, 2015:", { exact: false }),
    ).toBeInTheDocument();
    expect(steps.getByText("12.02")).toBeInTheDocument();
    expect(steps.getByText("7.68")).toBeInTheDocument();
    expect(steps.getByText("-4.34 percentage points")).toBeInTheDocument();
  });

  it("links the figures of the steps to the data they came from", () => {
    open(holdingClaim);
    const steps = section(t.recompute.heading);
    expect(
      steps.getByText(t.recompute.valuesFrom, { exact: false }),
    ).toBeInTheDocument();
    expect(
      steps.getByRole("link", { name: /Eurostat une_rt_m/ }),
    ).toHaveAttribute("href", holdingClaim.data?.url);
  });

  it("shows each calculation's notes, such as how a year's value was made", () => {
    open(holdingClaim);
    expect(screen.getByTestId("op-notes")).toHaveTextContent(
      `${t.recompute.note}: A year's value is the average of its 12 monthly values.`,
    );
  });

  it("folds a long list of figures, such as a whole series, behind its count", () => {
    const op = {
      ...holdingClaim.operations![0],
      inputs: Array.from({ length: 10 }, (_, i) => ({
        geo: "IT",
        period: String(2010 + i),
        value: i,
      })),
    };
    open({ ...holdingClaim, operations: [op] });
    const summary = screen.getByText(`${t.recompute.figuresUsed} (10)`);
    expect(summary.closest("details")).not.toHaveAttribute("open");
  });

  it("sets each figure claimed beside the official one, with the gap allowed", () => {
    open(holdingClaim);
    const compared = section(t.compared.heading);
    const start = within(
      compared.getByText("Start value").closest("li") as HTMLElement,
    );
    expect(start.getByText("11.9%")).toBeInTheDocument();
    expect(start.getByText("12.02%")).toBeInTheDocument();
    expect(start.getByText("±0.17%")).toBeInTheDocument();
    expect(start.getByText(t.compared.holds)).toBeInTheDocument();
  });

  it("says in words, not by colour alone, which parts do not hold", () => {
    open(partlyClaim);
    const compared = section(t.compared.heading);
    expect(compared.getAllByText(t.compared.fails)).toHaveLength(2);
    expect(compared.getAllByText(t.compared.holds)).toHaveLength(1);
    expect(compared.getByText("-12 points")).toBeInTheDocument();
    expect(compared.getByText("-10.7 points")).toBeInTheDocument();
  });

  it("says how to check it again, with a link to the same data", () => {
    open(holdingClaim);
    const verify = section(t.verify.heading);
    expect(verify.getAllByRole("listitem")).toHaveLength(4);
    expect(
      verify.getByRole("link", { name: /Eurostat une_rt_m/ }),
    ).toHaveAttribute("href", holdingClaim.data?.url);
    expect(
      verify.getByText(/has revised the series since November 7, 2026/),
    ).toBeInTheDocument();
  });

  it("keeps the fingerprint, the observations, the models and the versions in the technical details", () => {
    open(holdingClaim, {
      sharedModels: [
        { step: "extract", provider: "g", model: "x", label: "GPT-OSS 20B" },
      ],
    });
    const details = within(
      screen.getByText(t.technical.heading).closest("details") as HTMLElement,
    );
    expect(details.getByText("4f556131ab70")).toBeInTheDocument();
    expect(details.getByText("525")).toBeInTheDocument();
    expect(details.getByText("GPT-OSS 20B")).toBeInTheDocument();
    expect(
      details.getByText(/app 0.1.0, catalog 0.4.0, tolerances 2/),
    ).toBeInTheDocument();
  });

  it("lists each step once with a readable model name", () => {
    const models = [
      {
        step: "match",
        provider: "g",
        model: "gpt-oss-120b",
        label: "GPT-OSS 120B",
      },
      {
        step: "match",
        provider: "g",
        model: "gpt-oss-120b",
        label: "GPT-OSS 120B",
      },
      { step: "plan", provider: "g", model: "old-id", label: "" },
    ] as const;
    open(
      { ...holdingClaim, models: [...models] },
      {
        sharedModels: [
          { step: "extract", provider: "g", model: "x", label: "GPT-OSS 20B" },
        ],
      },
    );
    const names = (label: string) =>
      screen.getByText(label).nextElementSibling?.textContent;
    expect(names(strings.steps.extract)).toBe("GPT-OSS 20B");
    expect(names(strings.steps.match)).toBe("GPT-OSS 120B");
    expect(names(strings.steps.plan)).toBe("old-id");
    expect(screen.getAllByText("GPT-OSS 120B")).toHaveLength(1);
  });

  it("cites a second series used, such as the population", () => {
    const extra = {
      indicator: {
        ...holdingClaim.indicator!,
        id: "pop",
        name: "Total population (Eurostat)",
      },
      data: { ...holdingClaim.data!, dataset: "demo_pjan", url: "https://pop" },
    };
    open({ ...holdingClaim, extra_sources: [extra] });
    const series = section(t.series.heading);
    expect(series.getByText(t.series.alsoUsed)).toBeInTheDocument();
    expect(series.getByText("Total population (Eurostat)")).toBeInTheDocument();
    // Its link is among the sources of the figures, and its fingerprint is kept.
    expect(
      section(t.recompute.heading).getByRole("link", { name: /demo_pjan/ }),
    ).toHaveAttribute("href", "https://pop");
  });

  it("says so when no data was fetched, and leaves out what needs data", () => {
    open(unmatchedClaim);
    expect(screen.getByText(t.series.noData)).toBeInTheDocument();
    // How it was read is still worth seeing: a reader can rephrase.
    expect(screen.getByText(t.reading.heading)).toBeInTheDocument();
    for (const heading of [
      t.recompute.heading,
      t.compared.heading,
      t.verify.heading,
    ]) {
      expect(screen.queryByText(heading)).not.toBeInTheDocument();
    }
  });

  it("gives every section of every claim its own id, so several claims can share a page", () => {
    render(
      <>
        <Receipt claim={holdingClaim} versions={versions} />
        <Receipt claim={{ ...partlyClaim, index: 1 }} versions={versions} />
      </>,
    );
    const ids = [...document.querySelectorAll("[id]")].map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("CheckResultView", () => {
  const two = checkResult(
    [
      holdingClaim,
      {
        ...partlyClaim,
        index: 1,
        claim: { ...partlyClaim.claim, quote: "today it is 43.3%." },
      },
    ],
    { text: `${holdingClaim.claim.quote} Also, today it is 43.3%.` },
  );

  it("shows the text that was checked, each claim marked and numbered", () => {
    const { container } = render(<CheckResultView result={two} />);
    const original = within(
      screen.getByRole("region", { name: strings.check.originalHeading }),
    );
    expect(container.querySelectorAll("mark")).toHaveLength(2);
    expect(original.getByText("1")).toBeInTheDocument();
    expect(original.getByText("2")).toBeInTheDocument();
    expect(original.getByText(/Also,/)).toBeInTheDocument();
  });

  it("names each claim's section by its place among them", () => {
    render(<CheckResultView result={two} />);
    expect(
      screen.getByRole("heading", { level: 2, name: "Claim 1 of 2" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Claim 2 of 2" }),
    ).toBeInTheDocument();
  });

  it("does not repeat the text when it is only the claim", () => {
    render(<CheckResultView result={checkResult([holdingClaim])} />);
    expect(
      screen.queryByText(strings.check.originalHeading),
    ).not.toBeInTheDocument();
  });

  it("shows the words around a single claim", () => {
    render(
      <CheckResultView
        result={checkResult([holdingClaim], {
          text: `Renzi, 2013: ${holdingClaim.claim.quote}`,
        })}
      />,
    );
    expect(screen.getByText(strings.check.originalHeading)).toBeInTheDocument();
  });

  it("links the earlier check when the answer was reused", () => {
    render(
      <CheckResultView
        result={checkResult([holdingClaim], { cached_from: "abc-123" })}
      />,
    );
    expect(
      screen.getByText(strings.check.cached, { exact: false }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.cachedLink }),
    ).toHaveAttribute("href", "/check/abc-123");
  });

  it("says so when no claim with a number was found", () => {
    render(<CheckResultView result={checkResult([])} />);
    expect(screen.getByText(strings.check.noClaims)).toBeInTheDocument();
  });
});
