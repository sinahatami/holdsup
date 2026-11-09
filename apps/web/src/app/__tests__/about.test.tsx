import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/about/page";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { catalogEntry } from "@/test/fixtures";

const t = strings.about;
afterEach(() => vi.unstubAllGlobals());

const api = (indicators: ReturnType<typeof catalogEntry>[]) =>
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: "0.7.0", indicators }),
    }),
  );

describe("About page", () => {
  it("says what HoldsUp is, who it is for, and has a section for each", async () => {
    api([]);
    render(await Page());
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    expect(screen.getByText(t.intro)).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual([
      t.what.heading,
      t.who.heading,
      t.data.heading,
      t.open.heading,
      t.contribute.heading,
    ]);
    expect(screen.getAllByRole("listitem").length).toBeGreaterThan(
      t.who.items.length,
    );
  });

  it("names each source, links to it in a new tab, and counts its statistics from the catalog", async () => {
    api([
      catalogEntry({ id: "a", source: "Eurostat" }),
      catalogEntry({ id: "b", source: "Eurostat" }),
      catalogEntry({ id: "c", source: "the World Bank" }),
    ]);
    render(await Page());
    const eurostat = screen
      .getByRole("link", { name: /^Eurostat/ })
      .closest("li") as HTMLElement;
    expect(eurostat).toHaveTextContent("2 statistics");
    expect(
      within(eurostat).getByRole("link", { name: /Eurostat/ }),
    ).toHaveAttribute("target", "_blank");
    expect(
      screen.getByRole("link", { name: /^World Bank/ }).closest("li"),
    ).toHaveTextContent("1 statistic");
    // No entry from this source, so no count is claimed for it.
    expect(
      screen.getByRole("link", { name: /^Our World in Data/ }).closest("li"),
    ).not.toHaveTextContent(/\d statistic/);
  });

  it("still names the sources, without counts, when the catalog cannot be read", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(screen.getByRole("link", { name: /^Eurostat/ })).toBeInTheDocument();
    expect(screen.queryByText(/\d+ statistics?/)).not.toBeInTheDocument();
  });

  it("walks through adding a statistic, with the file and the command to use", async () => {
    api([]);
    render(await Page());
    const steps = screen
      .getByRole("heading", { level: 2, name: t.contribute.heading })
      .closest("section") as HTMLElement;
    expect(within(steps).getAllByRole("listitem")).toHaveLength(
      t.contribute.steps.length,
    );
    expect(within(steps).getByText("make catalog-check")).toBeInTheDocument();
    expect(
      within(steps).getByText("packages/catalog/indicators/<id>.yaml"),
    ).toBeInTheDocument();
    expect(within(steps).getByText(t.contribute.newSource)).toBeInTheDocument();
  });

  it("links to the repository, the method and the list of statistics", async () => {
    api([]);
    render(await Page());
    expect(screen.getByRole("link", { name: t.open.repo })).toHaveAttribute(
      "href",
      strings.footer.repoUrl,
    );
    expect(screen.getByRole("link", { name: t.what.method })).toHaveAttribute(
      "href",
      routes.methodology,
    );
    expect(screen.getByRole("link", { name: t.data.all })).toHaveAttribute(
      "href",
      routes.indicators,
    );
  });

  it("still reads in full, with no counts, when the catalog cannot be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Eurostat/ })).toBeInTheDocument();
    expect(screen.queryByText(/\d+ statistics?/)).not.toBeInTheDocument();
  });
});
