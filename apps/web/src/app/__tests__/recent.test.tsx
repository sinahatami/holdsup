import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/recent/page";
import { strings } from "@/lib/strings";
import { galleryClaim, galleryItem } from "@/test/fixtures";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const t = strings.recent;
afterEach(() => vi.unstubAllGlobals());

const api = (items: unknown[]) =>
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items }) }),
  );

describe("Recent checks page", () => {
  it("lists the checks the API gives, with filters and a note that a verdict is about the number", async () => {
    api([
      galleryItem({
        id: "a",
        claims: [galleryClaim({ quote: "First claim" })],
      }),
      galleryItem({
        id: "b",
        claims: [galleryClaim({ quote: "Second claim", geo: "FR" })],
      }),
    ]);
    render(await Page());
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    expect(screen.getByText("First claim")).toBeInTheDocument();
    expect(screen.getByText("Second claim")).toBeInTheDocument();
    expect(
      screen.getByRole("search", { name: t.filtersHeading }),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.home.neutrality.text)).toBeInTheDocument();
  });

  it("asks the API for every check at once", async () => {
    api([galleryItem({ id: "a" })]);
    render(await Page());
    const fetched = vi.mocked(fetch).mock.calls[0][0];
    expect(String(fetched)).toContain("/v1/gallery?limit=100");
  });

  it("says there are none yet, apart from the API being down", async () => {
    api([]);
    render(await Page());
    expect(screen.getByText(t.empty)).toBeInTheDocument();
    expect(screen.queryByRole("search")).not.toBeInTheDocument();
  });

  it("says so when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(screen.getByText(t.unavailable)).toBeInTheDocument();
    expect(screen.queryByText(t.empty)).not.toBeInTheDocument();
  });
});
