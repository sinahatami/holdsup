import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimCard } from "@/components/organisms/claim-card";
import { WindowHeatmap } from "@/components/organisms/window-heatmap";
import type { Sweep } from "@/lib/sweep";
import { strings } from "@/lib/strings";
import {
  holdingClaim,
  holdingSweep,
  partlyClaim,
  unmatchedClaim,
  versions,
} from "@/test/fixtures";

// A claim that could not be checked shows the check form, which uses the router.
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const t = strings.windows;

const draw = (sweep: Sweep = holdingSweep, threshold: number | null = 0.7) =>
  render(
    <WindowHeatmap sweep={sweep} direction="down" threshold={threshold} />,
  );

const chart = () => screen.getByRole("group", { name: t.chartLabel });
const readout = () =>
  document.getElementById(
    chart().getAttribute("aria-describedby")!.split(" ")[1],
  )!;

describe("WindowHeatmap", () => {
  it("says how often the claim's direction holds nearby, and how to read the chart", () => {
    draw();
    expect(
      screen.getByRole("heading", { name: t.heading, level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "The fall shows in all 15 nearby time windows. To hold up, a claim needs at least 70%.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Each square is a time window/),
    ).toBeInTheDocument();
  });

  it("draws a square per window, coloured by whether the fall shows, and outlines the claim's", () => {
    draw();
    const svg = screen.getByTestId("window-heatmap");
    const cells = svg.querySelectorAll("rect[data-state]");
    expect(cells).toHaveLength(105); // 15 years: 15 × 14 / 2 windows
    // 2010 to 2011 changed by 0: not a fall.
    const flat = svg.querySelector('rect[data-row="0"][data-col="1"]')!;
    expect(flat.getAttribute("data-state")).toBe("fails");
    expect(flat.getAttribute("fill")).toMatch(/^url\(#.+-hatch\)$/);
    const own = svg.querySelectorAll("rect[data-own]");
    expect(own).toHaveLength(1);
    expect(own[0]).toHaveAttribute("data-row", "5"); // 2015
    expect(own[0]).toHaveAttribute("data-col", "13"); // 2023
    expect(svg.querySelectorAll("rect[data-near]")).toHaveLength(15);
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("is reached with Tab and walked with the arrow keys, saying each window", () => {
    draw();
    const frame = chart();
    expect(frame).toHaveAttribute("tabindex", "0");
    expect(readout()).toHaveTextContent(
      "From 2015 to 2023: -4.34 points. The fall shows. This is the claim's own window.",
    );
    expect(readout()).toHaveAttribute("aria-live", "polite");

    fireEvent.focus(frame);
    expect(screen.getByTestId("active-window")).toBeInTheDocument();
    fireEvent.keyDown(frame, { key: "ArrowLeft" });
    expect(readout()).toHaveTextContent(
      "From 2015 to 2022: -3.92 points. The fall shows. A nearby window, so it counts towards the verdict.",
    );
    fireEvent.keyDown(frame, { key: "Home" });
    expect(readout()).toHaveTextContent(/From 2015 to 2010: not a time window/);
    fireEvent.keyDown(frame, { key: "End" });
    fireEvent.keyDown(frame, { key: "ArrowDown" });
    expect(readout()).toHaveTextContent(
      "From 2016 to 2024: -5.2 points. The fall shows.",
    );
    // Other keys are left to the page.
    const tab = fireEvent.keyDown(frame, { key: "Tab" });
    expect(tab).toBe(true);
    fireEvent.blur(frame);
    expect(screen.queryByTestId("active-window")).toBeNull();
  });

  it("says the window a pointer is on", () => {
    draw();
    const svg = screen.getByTestId("window-heatmap");
    const cell = svg.querySelector('rect[data-row="0"][data-col="1"]')!;
    fireEvent.pointerOver(cell);
    expect(readout()).toHaveTextContent(
      "From 2010 to 2011: 0 points. The fall does not show.",
    );
  });

  it("shows every window as a table on request", () => {
    draw();
    const toggle = screen.getByRole("button", { name: t.showTable });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table")).toBeNull();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveAccessibleName(t.hideTable);
    const table = screen.getByRole("table");
    expect(
      within(table).getByText(/Figures are in percentage points/),
    ).toBeInTheDocument();
    // Rows 2010 to 2023 (2024 starts no window), columns 2011 to 2024.
    expect(within(table).getAllByRole("rowheader")).toHaveLength(14);
    expect(within(table).getAllByRole("columnheader")).toHaveLength(14);
    const own = table.querySelector("td[data-own]")!;
    expect(own).toHaveTextContent("-4.34 ✓holds, the claim's window");
    expect(screen.getByRole("region", { name: t.tableLabel })).toHaveAttribute(
      "tabindex",
      "0",
    );

    fireEvent.click(toggle);
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("says when the claim is too short for a share, and leaves out the nearby box", () => {
    draw({
      ...holdingSweep,
      near_starts: [],
      near_ends: [],
      counted: 0,
      held: 0,
      share: null,
    });
    expect(screen.getByText(/too short a span/)).toBeInTheDocument();
    expect(screen.queryByText(t.legend.near)).toBeNull();
    expect(
      screen.getByTestId("window-heatmap").querySelectorAll("rect[data-near]"),
    ).toHaveLength(0);
  });

  it("starts a grid wider than its frame with the claim's window in view", () => {
    // jsdom lays nothing out: a 300px frame holding a 600px chart.
    const widths = vi
      .spyOn(HTMLElement.prototype, "scrollWidth", "get")
      .mockReturnValue(600);
    const client = vi
      .spyOn(HTMLElement.prototype, "clientWidth", "get")
      .mockReturnValue(300);
    draw();
    // The claim's column (2023) starts 34 + 13 × 12 = 190 units in, of 216; at 600 / 216
    // pixels a unit that is about 528px, minus half the frame.
    expect(chart().scrollLeft).toBeGreaterThan(300);
    widths.mockRestore();
    client.mockRestore();
  });

  it("leaves a grid that fits where it is", () => {
    draw();
    expect(chart().scrollLeft).toBe(0);
  });

  it("explains windows that start and end within the year", () => {
    const monthly: Sweep = {
      ...holdingSweep,
      starts: ["2019-03", "2020-03"],
      ends: ["2019-09", "2020-09"],
      values: [
        [1, 2],
        [null, 3],
      ],
      holds: [
        [false, false],
        [null, false],
      ],
      claim_start: "2019-03",
      claim_end: "2020-09",
      near_starts: [],
      near_ends: [],
      share: null,
    };
    draw(monthly);
    expect(
      screen.getByText(
        /same point in the year as the claim's own, March 2019 to September 2020/,
      ),
    ).toBeInTheDocument();
  });
});

describe("ClaimCard", () => {
  const card = (claim: typeof holdingClaim) =>
    render(
      <ClaimCard
        claim={claim}
        versions={versions}
        order={0}
        total={1}
        checkId="c1"
      />,
    );

  it("shows the heatmap for a claim the sweep looked at", () => {
    card(holdingClaim);
    expect(
      screen.getByRole("heading", { name: t.heading }),
    ).toBeInTheDocument();
  });

  it("leaves it out when there is no sweep, or nothing could be checked", () => {
    card(partlyClaim);
    expect(screen.queryByRole("heading", { name: t.heading })).toBeNull();
  });

  it("leaves it out for a claim that could not be checked", () => {
    card({ ...unmatchedClaim, sweep: holdingSweep });
    expect(screen.queryByRole("heading", { name: t.heading })).toBeNull();
  });
});
