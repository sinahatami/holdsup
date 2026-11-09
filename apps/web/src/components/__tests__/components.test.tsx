import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CheckForm } from "@/components/organisms/check-form";
import { Gallery } from "@/components/organisms/gallery";
import { SampleReceipt } from "@/components/organisms/sample-receipt";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { CatalogList } from "@/components/organisms/catalog-list";
import { ClaimCard } from "@/components/organisms/claim-card";
import { Receipt } from "@/components/organisms/receipt";
import { Trace } from "@/components/organisms/trace";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { CatalogEntry, ClaimResult, GalleryItem } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

describe("VerdictBadge", () => {
  it.each(Object.keys(strings.verdicts) as (keyof typeof strings.verdicts)[])(
    "names the %s verdict in words",
    (label) => {
      render(<VerdictBadge label={label} />);
      expect(screen.getByText(strings.verdicts[label])).toBeInTheDocument();
    },
  );
});

describe("Trace", () => {
  it("lists steps with a text state", () => {
    render(
      <Trace
        rows={[
          {
            key: "all:extract",
            step: "extract",
            claim: null,
            state: "ok",
            summary: "1 claim",
            models: [],
            ms: 3,
          },
          {
            key: "0:match",
            step: "match",
            claim: 0,
            state: "running",
            summary: "",
            models: [],
            ms: null,
          },
        ]}
      />,
    );
    expect(screen.getByText(/done/)).toBeInTheDocument();
    expect(screen.getByText(/running/)).toBeInTheDocument();
  });
  it("renders nothing without rows", () => {
    const { container } = render(<Trace rows={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Gallery", () => {
  it("links each item to its check", () => {
    render(
      <Gallery
        items={[
          {
            id: "abc",
            text: "A claim",
            created_at: "",
            verdicts: ["supported"],
            indicators: [],
            claims: [{ quote: "A claim", label: "supported" }],
          },
        ]}
      />,
    );
    expect(screen.getByRole("link", { name: "A claim" })).toHaveAttribute(
      "href",
      "/check/abc",
    );
  });
});

const item = (
  claims: GalleryItem["claims"],
  text = "Some text.",
): GalleryItem => ({
  id: "x",
  text,
  created_at: "",
  verdicts: claims.map((c) => c.label),
  indicators: [],
  claims,
});

describe("GalleryCard", () => {
  it("shows the claimed figure beside the official one, with source and year", () => {
    render(
      <GalleryCard
        item={item([
          {
            quote: "Debt is 133.6% of GDP.",
            label: "supported",
            claimed: 133.6,
            official: 132.6,
            unit: "% of GDP",
            indicator: "Government debt",
            source: "eurostat",
            period: "2024",
          },
        ])}
      />,
    );
    const line = screen.getByText(/Claimed/).closest("p")!;
    expect(line).toHaveTextContent(/Claimed 133\.6% official 132\.6%/);
    expect(line).toHaveTextContent("Eurostat, 2024");
    // One claim: no summary, and the quote is not repeated under the text.
    expect(screen.queryByText(/claims hold up/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("Debt is 133.6% of GDP."),
    ).not.toBeInTheDocument();
  });

  it("says a long unit once, after the official figure", () => {
    render(
      <GalleryCard
        item={item([
          {
            quote: "q",
            label: "supported",
            claimed: 1.18,
            official: 1.18,
            unit: "live births per woman",
            source: "eurostat",
            period: "2024",
          },
        ])}
      />,
    );
    expect(screen.getByText(/Claimed/).closest("p")).toHaveTextContent(
      /Claimed 1\.18 official 1\.18 live births per woman/,
    );
  });

  it("falls back to what it was checked against when there is no figure", () => {
    render(
      <GalleryCard
        item={item([
          {
            quote: "q",
            label: "supported",
            indicator: "Unemployment rate",
            source: "eurostat",
          },
        ])}
      />,
    );
    expect(
      screen.getByText("Checked against Unemployment rate (Eurostat)"),
    ).toBeInTheDocument();
  });

  it("says so when nothing could be compared", () => {
    render(<GalleryCard item={item([{ quote: "q", label: "cant_check" }])} />);
    expect(screen.getByText(strings.home.card.noFigure)).toBeInTheDocument();
  });

  it("names each claim and summarises when there are several", () => {
    render(
      <GalleryCard
        item={item(
          [
            { quote: "Debt is 133% of GDP.", label: "supported" },
            { quote: "Growth was 3% in 2023.", label: "not_supported" },
          ],
          "Debt is 133% of GDP and growth was 3% in 2023.",
        )}
      />,
    );
    expect(screen.getByText("1 of 2 claims hold up")).toBeInTheDocument();
    const rows = screen.getAllByRole("listitem");
    // Each badge sits in a row with the claim it belongs to.
    const row = (quote: string) =>
      rows.find((r) => within(r).queryByText(quote) && !r.querySelector("ul"))!;
    expect(
      within(row("Debt is 133% of GDP.")).getByText(strings.verdicts.supported),
    ).toBeInTheDocument();
    expect(
      within(row("Growth was 3% in 2023.")).getByText(
        strings.verdicts.not_supported,
      ),
    ).toBeInTheDocument();
  });

  it("still shows the verdicts when the API sent no per-claim data", () => {
    render(
      <GalleryCard
        item={
          {
            id: "x",
            text: "t",
            created_at: "",
            verdicts: ["partly_supported"],
            indicators: [],
          } as unknown as GalleryItem
        }
      />,
    );
    expect(
      screen.getByText(strings.verdicts.partly_supported),
    ).toBeInTheDocument();
  });
});

describe("SampleReceipt", () => {
  it("walks from the claim to the verdict", () => {
    render(<SampleReceipt />);
    const s = strings.home.sample;
    for (const text of [s.claim, s.series, s.source, s.recomputed]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    expect(screen.getByText(strings.verdicts.supported)).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("opens a real receipt when given one", () => {
    render(<SampleReceipt href="/check/abc" />);
    expect(
      screen.getByRole("link", { name: strings.home.sample.open }),
    ).toHaveAttribute("href", "/check/abc");
  });
});

const claim = {
  index: 0,
  indicator: {
    id: "i",
    name: "Unemployment rate",
    source: "eurostat",
    source_code: "x",
    unit: "%",
    frequency: "A",
    definition: "Share unemployed",
  },
  data: {
    source: "Eurostat",
    dataset: "une_rt_a",
    url: "https://e.u",
    retrieved_at: "2026-11-07",
    raw_sha256: "ab12",
    label: "",
    places: [],
    rows: 2,
  },
  operations: [
    {
      op: "change",
      args: { start: "2015", end: "2023" },
      inputs: [{ geo: "IT", period: "2015", value: 11.9 }],
      value: -4.2,
      extras: {},
      series: null,
      unit: "pp",
      flags: [],
    },
  ],
  models: [
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
  ],
} as unknown as ClaimResult;

describe("Receipt", () => {
  it("shows source, fingerprint, operations and versions", () => {
    render(
      <Receipt
        claim={claim}
        versions={{ app: "0.1.0", catalog: "0.2.0", tolerances: 1 }}
      />,
    );
    expect(screen.getByText("Unemployment rate")).toBeInTheDocument();
    expect(screen.getByText("ab12")).toBeInTheDocument();
    expect(screen.getByText(/change\(/)).toBeInTheDocument();
    expect(screen.getByText(/catalog 0.2.0/)).toBeInTheDocument();
    expect(screen.queryByTestId("op-notes")).not.toBeInTheDocument();
  });
  it("lists each step once with a readable model name", () => {
    render(
      <Receipt
        claim={claim}
        versions={{ app: "0.0.0+d264e60", catalog: "0.6.0", tolerances: 2 }}
        sharedModels={[
          { step: "extract", provider: "g", model: "x", label: "GPT-OSS 20B" },
        ]}
      />,
    );
    const names = (label: string) =>
      screen.getByText(label).nextElementSibling?.textContent;
    expect(names(strings.steps.extract)).toBe("GPT-OSS 20B");
    expect(names(strings.steps.match)).toBe("GPT-OSS 120B");
    expect(names(strings.steps.plan)).toBe("old-id");
    expect(screen.getAllByText("GPT-OSS 120B")).toHaveLength(1);
    expect(screen.getByText(/app 0.0.0\+d264e60/)).toBeInTheDocument();
  });
  it("cites a second series used, such as the population", () => {
    const extra = {
      indicator: { ...claim.indicator!, name: "Total population (Eurostat)" },
      data: { ...claim.data!, dataset: "demo_pjan" },
    };
    render(
      <Receipt
        claim={{ ...claim, extra_sources: [extra] } as ClaimResult}
        versions={{ app: "a", catalog: "c", tolerances: 1 }}
      />,
    );
    expect(screen.getByText(strings.receipt.alsoUsed)).toBeInTheDocument();
    expect(screen.getByText("demo_pjan")).toBeInTheDocument();
  });
  it("shows each calculation's notes, such as how a year's value was made", () => {
    const detail =
      "each year's value is the average of its 12 monthly values; complete years only (2015, 2023)";
    const op = {
      ...claim.operations![0],
      flags: [{ code: "annual_value", detail, items: [] }],
    };
    render(
      <Receipt
        claim={{ ...claim, operations: [op] } as ClaimResult}
        versions={{ app: "a", catalog: "0.3.0", tolerances: 1 }}
      />,
    );
    expect(screen.getByTestId("op-notes")).toHaveTextContent(
      `${strings.receipt.note}: ${detail}`,
    );
  });
  it("says so when no data was fetched", () => {
    render(
      <Receipt
        claim={{
          ...claim,
          data: null,
          indicator: null,
          operations: [],
          models: [],
        }}
        versions={{ app: "a", catalog: "c", tolerances: 1 }}
      />,
    );
    expect(screen.getByText(strings.receipt.noData)).toBeInTheDocument();
  });
});

describe("CheckForm", () => {
  it("fills the box from an example and posts it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "new-id" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<CheckForm />);
    fireEvent.click(
      screen.getByRole("button", { name: strings.home.examples[0] }),
    );
    fireEvent.click(screen.getByRole("button", { name: strings.home.submit }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/check/new-id"));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      text: strings.home.examples[0],
    });
    vi.unstubAllGlobals();
  });

  it("shows the problem detail when the API refuses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        statusText: "x",
        json: async () => ({
          title: "Too many",
          status: 429,
          detail: "Slow down.",
        }),
      }),
    );
    render(<CheckForm />);
    fireEvent.change(screen.getByLabelText(strings.home.inputLabel), {
      target: { value: "claim" },
    });
    fireEvent.click(screen.getByRole("button", { name: strings.home.submit }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Slow down.");
    vi.unstubAllGlobals();
  });

  it("blocks text over the limit", () => {
    render(<CheckForm />);
    fireEvent.change(screen.getByLabelText(strings.home.inputLabel), {
      target: { value: "x".repeat(2001) },
    });
    expect(
      screen.getByRole("button", { name: strings.home.submit }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(strings.home.tooLong);
  });
});

const versions = { app: "a", catalog: "c", tolerances: 1 };
const cantCheck = {
  ...claim,
  claim: { quote: "Italy has 20 millions population in 2022" },
  verdict: { label: "cant_check", reason: "HoldsUp can't check this yet." },
  explanation: "",
  retryable: false,
  suggestions: [{ id: "a", name: "Total population (Eurostat)" }],
} as unknown as ClaimResult;

describe("ClaimCard", () => {
  it("offers the closest statistics and the full list when it can't check", () => {
    render(<ClaimCard claim={cantCheck} versions={versions} order={0} />);
    expect(screen.getByText("Total population (Eurostat)")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.seeAll }),
    ).toHaveAttribute("href", "/indicators");
    expect(
      screen.queryByText(strings.check.explanationHeading),
    ).not.toBeInTheDocument();
  });
  it("does not point to the list when the source was only briefly down", () => {
    render(
      <ClaimCard
        claim={{ ...cantCheck, retryable: true } as ClaimResult}
        versions={versions}
        order={0}
      />,
    );
    expect(
      screen.queryByRole("link", { name: strings.check.seeAll }),
    ).not.toBeInTheDocument();
  });
  it("shows Why when there is something to add", () => {
    render(
      <ClaimCard
        claim={
          {
            ...claim,
            claim: { quote: "q" },
            verdict: { label: "not_supported", reason: "Outside tolerance." },
            explanation: "Eurostat counts 59 million.",
          } as unknown as ClaimResult
        }
        versions={versions}
        order={0}
      />,
    );
    expect(screen.getByText("Eurostat counts 59 million.")).toBeInTheDocument();
  });
});

describe("CatalogList", () => {
  const entry = (id: string, name: string, theme: CatalogEntry["theme"]) => ({
    id,
    name,
    theme,
    definition: "What it measures.",
    unit: "persons",
    source: "Eurostat",
    frequency: "annual",
    first_year: 1960,
    last_year: null,
  });

  it("shows what each statistic measures and where it comes from", () => {
    render(
      <CatalogList entries={[entry("p", "Total population", "population")]} />,
    );
    expect(screen.getByText("Total population")).toBeInTheDocument();
    expect(
      screen.getByText(/persons · Eurostat · since 1960/),
    ).toBeInTheDocument();
  });

  it("groups by theme in the page's order, with a count for each", () => {
    render(
      <CatalogList
        entries={[
          entry("a", "Homicide rate", "safety"),
          entry("b", "Median age", "population"),
          entry("c", "Total population", "population"),
        ]}
      />,
    );
    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(headings).toEqual(["Population", "Safety"]); // no empty themes
    const population = screen.getByRole("region", { name: "Population" });
    expect(
      within(population)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(["Median age", "Total population"]);
    expect(within(population).getByText("2 statistics")).toBeInTheDocument();
    expect(screen.getByText("1 statistic")).toBeInTheDocument();
    expect(screen.getByText("3 statistics")).toBeInTheDocument();
  });

  it("links each topic from the jump list", () => {
    render(
      <CatalogList
        entries={[
          entry("a", "Homicide rate", "safety"),
          entry("b", "Median age", "population"),
        ]}
      />,
    );
    const nav = screen.getByRole("navigation", {
      name: strings.indicators.themesNav,
    });
    expect(within(nav).getByRole("link", { name: /Safety/ })).toHaveAttribute(
      "href",
      "#theme-safety",
    );
    expect(
      within(nav).getByRole("link", { name: /Population/ }),
    ).toHaveAttribute("href", "#theme-population");
  });
});
