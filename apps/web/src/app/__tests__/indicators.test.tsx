import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Page from "@/app/indicators/page";
import { strings } from "@/lib/strings";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("Indicators page", () => {
  it("lists what HoldsUp can check", async () => {
    const indicators = [
      {
        id: "p",
        name: "Total population (Eurostat)",
        definition: "People resident on 1 January.",
        unit: "persons",
        source: "Eurostat",
        frequency: "annual",
        first_year: 1960,
        last_year: null,
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ version: "0.5.0", indicators }),
      }),
    );
    render(await Page());
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: strings.indicators.heading,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Total population (Eurostat)")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
  it("says so when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(
      screen.getByText(strings.indicators.unavailable),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
