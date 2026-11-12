import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProviderStatusTable } from "@/components/organisms/provider-status";
import { strings } from "@/lib/strings";
import { statusResponse } from "@/test/fixtures";

const t = strings.status;

describe("ProviderStatusTable", () => {
  it("renders a row per provider from the router's data", () => {
    render(<ProviderStatusTable status={statusResponse} />);
    expect(
      screen.getByText("1 of 3 providers are ready; checks use those."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("As of November 12, 2026, 21:40 UTC."),
    ).toBeInTheDocument();
    const table = within(
      screen.getByRole("region", { name: t.caption }),
    ).getByRole("table");
    expect(table).toHaveAccessibleName(t.caption);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.getAttribute("data-state"))).toEqual([
      "ready",
      "cooling_down",
      "out_of_budget",
    ]);
    const groq = within(rows[0]);
    expect(
      groq.getByRole("rowheader", { name: "GPT-OSS 120B (Groq)" }),
    ).toBeInTheDocument();
    expect(groq.getByText("Ready")).toBeInTheDocument();
    expect(groq.getByText("812 of 900")).toBeInTheDocument();
    expect(
      within(rows[1]).getByText("Cooling down, ready in about 15 seconds"),
    ).toBeInTheDocument();
    expect(within(rows[1]).getByText(t.noLimit)).toBeInTheDocument();
    expect(within(rows[2]).getByText("0 of 45")).toBeInTheDocument();
    // Each state has an icon beside its words, hidden from screen readers.
    expect(rows[2].querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText(t.capNote)).toBeInTheDocument();
  });

  it("says plainly when the API does not answer", () => {
    render(<ProviderStatusTable status={null} />);
    expect(screen.getByText(t.down)).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
