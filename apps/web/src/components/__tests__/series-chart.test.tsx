import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimCard } from "@/components/organisms/claim-card";
import { SeriesChart } from "@/components/organisms/series-chart";
import type { ClaimResult } from "@/lib/api/client";
import { chartOf, type Chart } from "@/lib/series-chart";
import { strings } from "@/lib/strings";
import { holdingClaim, unmatchedClaim, versions } from "@/test/fixtures";

// A claim that could not be checked shows the check form, which uses the router.
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const t = strings.chart;
const UNIT = "% of labour force aged 15-74";

const draw = (chart: Chart = chartOf(holdingClaim)!) =>
  render(<SeriesChart chart={chart} />);

const frame = () => screen.getByRole("group", { name: t.chartLabel });
const readout = () =>
  document.getElementById(
    frame().getAttribute("aria-describedby")!.split(" ")[1],
  )!;
const svg = () => screen.getByTestId("series-chart");

describe("SeriesChart", () => {
  it("says what the series is, the claim's window, and that these are the values as read", () => {
    draw();
    expect(
      screen.getByRole("heading", { name: t.heading, level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `Italy, 2000 to 2025, in ${UNIT}. The shaded band is the claim's window, 2015 to 2023.`,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(t.asRead)).toBeInTheDocument();
  });

  it("draws the line, the window, the values used and the values the claim states", () => {
    draw();
    expect(screen.getByTestId("chart-line").getAttribute("d")).toMatch(
      /^M[^M]+$/, // every year has a value: one unbroken line
    );
    expect(screen.getByTestId("chart-window")).toBeInTheDocument();
    const used = svg().querySelectorAll("circle[data-used]");
    expect([...used].map((c) => c.getAttribute("data-used"))).toEqual([
      "2015",
      "2023",
    ]);
    const claimed = svg().querySelectorAll("g[data-claimed]");
    expect([...claimed].map((g) => g.getAttribute("data-claimed"))).toEqual([
      "2015",
      "2023",
    ]);
    // Each claimed value has its allowed gap as a bar and a hollow diamond.
    expect(claimed[0].querySelectorAll("path")).toHaveLength(2);
    expect(screen.queryByTestId("chart-fit")).toBeNull();
  });

  it("is hidden from screen readers, which get a focusable frame that reads each value", () => {
    draw();
    expect(svg()).toHaveAttribute("aria-hidden", "true");
    expect(frame()).toHaveAttribute("tabindex", "0");
    expect(frame()).toHaveAttribute("dir", "ltr");
    expect(readout()).toHaveAttribute("aria-live", "polite");
    // It opens on the end of the claim's window.
    expect(readout()).toHaveTextContent(
      `2023: 7.68${UNIT}. ${t.notes.windowEnd} ${t.notes.used}`,
    );
  });

  it("moves between values with the arrow keys, Home and End", () => {
    draw();
    expect(screen.queryByTestId("active-point")).toBeNull();
    fireEvent.focus(frame());
    expect(screen.getByTestId("active-point")).toBeInTheDocument();
    fireEvent.keyDown(frame(), { key: "ArrowLeft" });
    expect(readout()).toHaveTextContent(
      `2022: 8.11${UNIT}. ${t.notes.inWindow}`,
    );
    fireEvent.keyDown(frame(), { key: "Home" });
    expect(readout()).toHaveTextContent(`2000: 10.1${UNIT}.`);
    fireEvent.keyDown(frame(), { key: "ArrowLeft" });
    expect(readout()).toHaveTextContent(`2000: 10.1${UNIT}.`);
    fireEvent.keyDown(frame(), { key: "End" });
    expect(readout()).toHaveTextContent(`2025: 6.02${UNIT}.`);
    fireEvent.blur(frame());
    expect(screen.queryByTestId("active-point")).toBeNull();
  });

  it("tells the marks apart by shape in its key", () => {
    draw();
    const key = screen.getByText(t.legend.line).closest("ul")!;
    expect(
      within(key)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual([
      t.legend.line,
      t.legend.window,
      t.legend.used,
      t.legend.claimed,
    ]);
  });

  it("draws a trend's fitted line and names it", () => {
    const chart = chartOf(holdingClaim)!;
    draw({ ...chart, used: [], fit: { start: 11.8, end: 7.9 } });
    expect(screen.getByTestId("chart-fit")).toBeInTheDocument();
    expect(screen.getByText(t.legend.fit)).toBeInTheDocument();
    expect(screen.queryByText(t.legend.used)).toBeNull();
  });

  it("lists every value with its notes in a table", () => {
    draw();
    const toggle = screen.getByRole("button", { name: t.showTable });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveTextContent(t.hideTable);
    const table = within(
      screen.getByRole("region", { name: t.tableLabel }),
    ).getByRole("table");
    expect(table).toHaveAccessibleName(t.tableCaption(UNIT));
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(27); // a header and 26 years
    const row2015 = within(table).getByRole("rowheader", {
      name: "2015",
    }).parentElement!;
    expect(row2015).toHaveTextContent("12.02");
    expect(row2015).toHaveTextContent(t.notes.windowStart);
    expect(row2015).toHaveTextContent(
      t.notes.claimed(`11.9${UNIT}`, "±0.17", true),
    );
  });
});

describe("the chart on a claim card", () => {
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

  it("comes before the other time windows", () => {
    card(holdingClaim);
    const chart = section()!;
    const windows = screen.getByRole("region", {
      name: strings.windows.heading,
    });
    expect(
      chart.compareDocumentPosition(windows) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("is left out without a series", () => {
    card({ ...holdingClaim, series: null });
    expect(section()).toBeNull();
  });

  it("is left out of a claim that can't be checked", () => {
    card({ ...unmatchedClaim, series: holdingClaim.series });
    expect(section()).toBeNull();
  });
});
