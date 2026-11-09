import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/methodology/page";
import { AllowedGaps } from "@/components/organisms/allowed-gaps";
import { MethodSteps } from "@/components/organisms/method-steps";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { tolerances } from "@/test/fixtures";

const t = strings.methodology;

afterEach(() => vi.unstubAllGlobals());

describe("AllowedGaps", () => {
  const gapOf = (label: string) => screen.getByText(label).closest("div");

  it("names the version the numbers come from", () => {
    render(<AllowedGaps tolerances={{ ...tolerances, version: 7 }} />);
    expect(screen.getByText(/\(version 7\)/)).toBeInTheDocument();
  });

  it("states each kind's gap from the rule's own numbers", () => {
    render(<AllowedGaps tolerances={tolerances} />);
    expect(gapOf(t.gaps.kinds.level.label)).toHaveTextContent(
      "Half a unit of the last digit written (“2.3” allows 0.05). Then 1% of the claimed figure is added",
    );
    expect(gapOf(t.gaps.kinds.absolute.label)).toHaveTextContent(
      "The largest of 5% of the claimed figure and half a unit of the last digit written",
    );
    expect(gapOf(t.gaps.kinds.percentage_points.label)).toHaveTextContent(
      "The largest of 0.5 points and half a unit of the last digit written",
    );
    expect(gapOf(t.gaps.kinds.ratio.label)).toHaveTextContent(
      /^.*5% of the claimed figure\.$/,
    );
    expect(gapOf(t.gaps.kinds.rank.label)).toHaveTextContent(t.gaps.exact);
  });

  it("follows the numbers when a rule changes", () => {
    render(
      <AllowedGaps
        tolerances={{
          ...tolerances,
          values: {
            ...tolerances.values,
            ratio: { ...tolerances.values.ratio, relative: 0.1 },
          },
        }}
      />,
    );
    expect(
      screen.getByText(t.gaps.kinds.ratio.label).closest("div"),
    ).toHaveTextContent("10% of the claimed figure.");
  });

  it("lists the other thresholds", () => {
    render(<AllowedGaps tolerances={tolerances} />);
    expect(
      screen.getByText(/within 2% of the start value/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/at least 50% of the ups and downs/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /1 year for yearly series, 1 half-year for half-yearly series, 2 quarters for quarterly series, and 3 months for monthly series/,
      ),
    ).toBeInTheDocument();
  });
});

describe("MethodSteps", () => {
  it("lists every step in order, and says who does each one", () => {
    render(<MethodSteps />);
    const steps = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(steps).toHaveLength(8);
    expect(steps[0]).toHaveTextContent("It looks for an earlier check");
    expect(steps[6]).toHaveTextContent("It decides the verdict");
    expect(steps[6]).toHaveTextContent(t.by.code);
    expect(steps[1]).toHaveTextContent(t.by.model);
    expect(steps[2]).toHaveTextContent(t.by.both);
  });
});

describe("Methodology page", () => {
  const api = (body: unknown) =>
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => body }),
    );

  it("has one heading, a section for each part, and a way to jump to each", async () => {
    api(tolerances);
    render(await Page());
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual(Object.values(t.sections));
    const nav = screen.getByRole("navigation", { name: t.onThisPage });
    expect(within(nav).getAllByRole("link")).toHaveLength(
      Object.keys(t.sections).length,
    );
    expect(
      within(nav).getByRole("link", { name: t.sections.limits }),
    ).toHaveAttribute("href", "#limits");
  });

  it("prints the allowed gaps it was given", async () => {
    api({ ...tolerances, version: 5 });
    render(await Page());
    expect(screen.getByText(/\(version 5\)/)).toBeInTheDocument();
  });

  it("does not say other time windows are compared", async () => {
    api(tolerances);
    render(await Page());
    expect(
      screen.getByText(/Other time windows are not compared yet\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/does not yet compare other time windows/),
    ).toBeInTheDocument();
  });

  it("says so, and still explains the rest, when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(screen.getByText(t.gaps.unavailable)).toBeInTheDocument();
    expect(screen.getByText(t.steps[0].title)).toBeInTheDocument();
  });

  it("points to what can be checked, and to the code", async () => {
    api(tolerances);
    render(await Page());
    expect(
      screen.getByRole("link", { name: t.cannotCatalog.link }),
    ).toHaveAttribute("href", routes.indicators);
    expect(screen.getByRole("link", { name: t.verify.link })).toHaveAttribute(
      "href",
      strings.footer.repoUrl,
    );
  });
});
