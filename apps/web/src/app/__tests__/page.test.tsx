import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Home from "@/app/page";
import { strings } from "@/lib/strings";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("Home page", () => {
  it("renders the title, the form and three examples, even with the API down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Home());
    expect(
      screen.getByRole("heading", { level: 1, name: strings.appName }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(strings.home.inputLabel)).toBeInTheDocument();
    for (const ex of strings.home.examples) {
      expect(screen.getByRole("button", { name: ex })).toBeInTheDocument();
    }
    expect(screen.getByText(strings.home.galleryEmpty)).toBeInTheDocument();
    // The sample receipt is static, so it is there too.
    expect(
      within(
        screen.getByRole("region", { name: strings.home.sample.heading }),
      ).getByText(strings.home.sample.claim),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("opens a real receipt for the sample when the gallery has the same claim", async () => {
    const gallery = [
      {
        id: "real-1",
        text: strings.home.sample.claim,
        created_at: "",
        verdicts: ["supported"],
        indicators: [],
        claims: [{ quote: strings.home.sample.claim, label: "supported" }],
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ items: gallery }),
      }),
    );
    render(await Home());
    expect(
      screen.getByRole("link", { name: strings.home.sample.open }),
    ).toHaveAttribute("href", "/check/real-1");
    vi.unstubAllGlobals();
  });

  it("renders the featured checks it fetched at build time", async () => {
    const items = [
      {
        id: "a1",
        text: "Debt is 133% of GDP.",
        created_at: "",
        verdicts: ["not_supported"],
        indicators: [],
        claims: [{ quote: "Debt is 133% of GDP.", label: "not_supported" }],
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items }) }),
    );
    render(await Home());
    expect(
      screen.getByRole("link", { name: "Debt is 133% of GDP." }),
    ).toHaveAttribute("href", "/check/a1");
    expect(
      screen.getByText(strings.verdicts.not_supported),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
