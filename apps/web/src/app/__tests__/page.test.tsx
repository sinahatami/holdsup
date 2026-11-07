import { render, screen } from "@testing-library/react";
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
    vi.unstubAllGlobals();
  });
});
