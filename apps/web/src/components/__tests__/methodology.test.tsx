import { act, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/methodology/page";
import { AllowedGaps } from "@/components/organisms/allowed-gaps";
import { MethodSteps } from "@/components/organisms/method-steps";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { externalLink } from "@/test/external";
import { tolerances } from "@/test/fixtures";

const t = strings.methodology;

afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = "";
});

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
        /over at least 2 years is also redone with its start moved up to 2 years either way and its end up to 2 years earlier\. To hold up, it has to go the same way in at least 70% of those time windows/,
      ),
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

  it("opens with a short summary, and folds the working away", async () => {
    api(tolerances);
    render(await Page());
    const summary = screen.getByRole("list", { name: t.glanceLabel });
    expect(within(summary).getAllByRole("listitem")).toHaveLength(
      t.glance.length,
    );
    const folded = (name: string) =>
      screen.getByRole("heading", { level: 2, name }).closest("details");
    for (const name of [t.sections.steps, t.sections.ops, t.sections.match]) {
      expect(folded(name)).not.toBeNull();
      expect(folded(name)).not.toHaveAttribute("open");
    }
    // What a verdict means and what it cannot do stay in view.
    for (const name of [
      t.sections.verdicts,
      t.sections.cannot,
      t.sections.limits,
    ]) {
      expect(folded(name)).toBeNull();
    }
  });

  it("opens a folded section when its link is followed, on arrival or later", async () => {
    api(tolerances);
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    window.location.hash = "#ops";
    render(await Page());
    const details = (name: string) =>
      screen.getByRole("heading", { level: 2, name }).closest("details");
    expect(details(t.sections.ops)).toHaveAttribute("open");
    expect(details(t.sections.steps)).not.toHaveAttribute("open");
    expect(scrollIntoView).toHaveBeenCalled();

    act(() => {
      window.location.hash = "#match";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(details(t.sections.match)).toHaveAttribute("open");
  });

  it("prints the allowed gaps it was given", async () => {
    api({ ...tolerances, version: 5 });
    render(await Page());
    expect(screen.getByText(/\(version 5\)/)).toBeInTheDocument();
  });

  it("says other time windows are compared, and what is not yet", async () => {
    api(tolerances);
    render(await Page());
    expect(
      screen.getByText(/holds in at least 70% of comparable time windows\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/start and end moved by a few years/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/does not yet look at per-person or inflation-adjusted/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/not compared yet/)).toBeNull();
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
    externalLink(t.verify.link, strings.footer.repoUrl);
  });
});
