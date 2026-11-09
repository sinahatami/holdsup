import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CanCheck } from "@/components/organisms/can-check";
import { CheckForm } from "@/components/organisms/check-form";
import { Gallery } from "@/components/organisms/gallery";
import { SampleReceipt } from "@/components/organisms/sample-receipt";
import { CharCounter } from "@/components/molecules/char-counter";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { CatalogList } from "@/components/organisms/catalog-list";
import { ClaimCard } from "@/components/organisms/claim-card";
import { Trace } from "@/components/organisms/trace";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { CatalogEntry, ClaimResult, GalleryItem } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import {
  catalogEntry,
  holdingClaim,
  unmatchedClaim,
  versions,
} from "@/test/fixtures";

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

  it("says a verdict is about the number, not the speaker, and links the method", () => {
    render(<Gallery items={[]} />);
    expect(
      screen.getByRole("link", { name: strings.home.neutrality.link }),
    ).toHaveAttribute("href", routes.methodology);
    expect(
      screen.getByText(/not about the person who said it/),
    ).toBeInTheDocument();
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

describe("CanCheck", () => {
  const e = (id: string, source: string, first: number, last: number | null) =>
    catalogEntry({ id, source, first_year: first, last_year: last });

  it("shows counts and sources taken from the catalog", () => {
    render(
      <CanCheck
        entries={[
          e("a", "Eurostat", 1983, null),
          e("b", "Eurostat", 1990, null),
          e("c", "the World Bank", 1960, null),
        ]}
      />,
    );
    const stat = (label: string) =>
      screen.getByText(label).nextElementSibling?.textContent;
    expect(stat("statistics")).toBe("3");
    expect(stat("topic")).toBe("1");
    expect(stat("sources")).toBe("2");
    expect(stat(strings.home.coverage.years)).toBe("1960–now");
    expect(screen.getByText("World Bank")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.home.canCheckLink }),
    ).toHaveAttribute("href", "/indicators");
  });

  it("falls back to a plain pointer when there is no catalog", () => {
    render(<CanCheck />);
    expect(screen.getByText(strings.home.canCheckBody)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.home.canCheckLink }),
    ).toHaveAttribute("href", "/indicators");
    expect(screen.queryByText("statistics")).not.toBeInTheDocument();
  });
});

describe("CharCounter", () => {
  it("is quiet until it nears the limit", () => {
    render(<CharCounter count={100} max={2000} />);
    expect(screen.getByText("100 / 2,000")).toHaveClass(
      "text-muted-foreground",
    );
  });
  it("warns, and says how many are left, near the limit", () => {
    render(<CharCounter count={1850} max={2000} />);
    const el = screen.getByText(/1,850 \/ 2,000/);
    expect(el).toHaveTextContent("150 left");
    expect(el).toHaveClass("font-semibold");
    expect(el).not.toHaveClass("text-destructive");
  });
  it("turns red over the limit", () => {
    render(<CharCounter count={2001} max={2000} />);
    expect(screen.getByText(/2,001/)).toHaveClass("text-destructive");
  });
});

describe("CheckForm", () => {
  it("tells people to write in English, and ties that to the box", () => {
    render(<CheckForm />);
    const note = screen.getByText(strings.home.englishOnly);
    expect(screen.getByRole("textbox")).toHaveAccessibleDescription(
      expect.stringContaining(strings.home.englishOnly),
    );
    expect(note).toBeVisible();
  });

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

  it("is disabled while the box is empty, and says how to submit from the keyboard", () => {
    render(<CheckForm />);
    const box = screen.getByLabelText(strings.home.inputLabel);
    const button = screen.getByRole("button", { name: strings.home.submit });
    expect(button).toBeDisabled();
    fireEvent.change(box, { target: { value: "   " } });
    expect(button).toBeDisabled(); // whitespace is empty
    fireEvent.change(box, { target: { value: "claim" } });
    expect(button).toBeEnabled();
    expect(screen.getByText(strings.home.shortcut)).toBeInTheDocument();
    expect(box).toHaveAttribute(
      "aria-keyshortcuts",
      "Control+Enter Meta+Enter",
    );
  });

  it.each([
    ["Ctrl", { ctrlKey: true }],
    ["Cmd", { metaKey: true }],
  ])("submits on %s+Enter", async (_name, mods) => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "kb-id" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<CheckForm />);
    const box = screen.getByLabelText(strings.home.inputLabel);
    fireEvent.change(box, { target: { value: "Debt is 133% of GDP." } });
    fireEvent.keyDown(box, { key: "Enter", ...mods });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/check/kb-id"));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("does not submit on a plain Enter, or on the shortcut with nothing to check", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<CheckForm />);
    const box = screen.getByLabelText(strings.home.inputLabel);
    fireEvent.keyDown(box, { key: "Enter", ctrlKey: true }); // empty
    fireEvent.change(box, { target: { value: "claim" } });
    fireEvent.keyDown(box, { key: "Enter" }); // plain Enter: a new line
    expect(fetchMock).not.toHaveBeenCalled();
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

const card = (claim: ClaimResult, order = 0, total = 1) =>
  render(
    <ClaimCard
      claim={claim}
      versions={versions}
      order={order}
      total={total}
      checkId="c1"
    />,
  );

describe("ClaimCard", () => {
  it("offers the closest statistics and the full list when it can't check", () => {
    card(unmatchedClaim);
    expect(screen.getByText("Total population (Eurostat)")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.seeAll }),
    ).toHaveAttribute("href", "/indicators");
    expect(
      screen.queryByText(strings.check.explanationHeading),
    ).not.toBeInTheDocument();
  });
  it("does not point to the list when the source was only briefly down", () => {
    card({ ...unmatchedClaim, retryable: true });
    expect(
      screen.queryByRole("link", { name: strings.check.seeAll }),
    ).not.toBeInTheDocument();
  });
  it("says the verdict is about the number when a person is quoted", () => {
    const quoted = {
      ...holdingClaim,
      claim: { ...holdingClaim.claim, speaker: "A. Minister" },
    };
    const { rerender } = card(quoted);
    expect(
      screen.getByRole("link", { name: strings.home.neutrality.link }),
    ).toHaveAttribute("href", routes.methodology);
    rerender(
      <ClaimCard
        claim={holdingClaim}
        versions={versions}
        order={0}
        total={1}
        checkId="c1"
      />,
    );
    expect(
      screen.queryByRole("link", { name: strings.home.neutrality.link }),
    ).not.toBeInTheDocument();
  });
  it("shows Why when there is something to add", () => {
    card(holdingClaim);
    expect(screen.getByText(holdingClaim.explanation)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: strings.check.explanationHeading,
      }),
    ).toBeInTheDocument();
  });
  it("names each claim for a screen reader, by its place among them", () => {
    card(holdingClaim, 1, 3);
    expect(
      screen.getByRole("heading", { level: 2, name: "Claim 2 of 3" }),
    ).toBeInTheDocument();
  });
  it("calls a lone claim just a claim", () => {
    card(holdingClaim);
    expect(
      screen.getByRole("heading", { level: 2, name: "Claim" }),
    ).toBeInTheDocument();
  });
  it("lays the receipt open on the page", () => {
    card(holdingClaim);
    expect(screen.getByTestId("receipt")).toBeVisible();
  });
});

describe("CatalogList", () => {
  const entry = (id: string, name: string, theme: CatalogEntry["theme"]) =>
    catalogEntry({
      id,
      name,
      theme,
      definition: "What it measures.",
      unit: "persons",
      first_year: 1960,
      source_code: "demo_pjan",
      countries: ["IT", "NO"],
      groups: [],
    });

  it("shows what each statistic measures, its source, unit, years and places", () => {
    render(
      <CatalogList entries={[entry("p", "Total population", "population")]} />,
    );
    expect(screen.getByText("Total population")).toBeInTheDocument();
    expect(screen.getByText("What it measures.")).toBeInTheDocument();
    const facts = screen.getByText("Source").closest("dl");
    expect(facts).toHaveTextContent("Eurostat demo_pjan");
    expect(facts).toHaveTextContent("Measured inpersons");
    expect(facts).toHaveTextContent("Yearssince 1960");
    expect(facts).toHaveTextContent("CoversItaly and Norway");
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
  });
});
