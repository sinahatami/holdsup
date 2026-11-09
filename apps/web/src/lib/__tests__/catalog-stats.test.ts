import { describe, expect, it } from "vitest";
import type { CatalogEntry } from "@/lib/api/client";
import { coverage } from "@/lib/catalog-stats";

const entry = (
  over: Partial<CatalogEntry> & Pick<CatalogEntry, "id">,
): CatalogEntry => ({
  name: over.id,
  theme: "economy",
  definition: "d",
  unit: "%",
  source: "Eurostat",
  frequency: "annual",
  first_year: 2000,
  last_year: null,
  ...over,
});

describe("coverage", () => {
  it("is null for an empty catalog", () => {
    expect(coverage([])).toBeNull();
  });

  it("counts statistics, topics and the sources, largest first", () => {
    const c = coverage([
      entry({ id: "a", source: "the World Bank", theme: "work" }),
      entry({ id: "b" }),
      entry({ id: "c", theme: "work" }),
      entry({ id: "d", source: "Our World in Data" }),
      entry({ id: "e" }),
    ]);
    expect(c).toMatchObject({ statistics: 5, topics: 2 });
    expect(c?.sources).toEqual([
      { id: "Eurostat", count: 3 },
      { id: "Our World in Data", count: 1 },
      { id: "the World Bank", count: 1 },
    ]);
  });

  it("spans from the earliest year, and is open-ended while any series is updated", () => {
    expect(
      coverage([
        entry({ id: "a", first_year: 1983, last_year: 2020 }),
        entry({ id: "b", first_year: 1960, last_year: null }),
      ]),
    ).toMatchObject({ firstYear: 1960, lastYear: null });
  });

  it("ends at the latest year once every series has ended", () => {
    expect(
      coverage([
        entry({ id: "a", first_year: 1983, last_year: 2020 }),
        entry({ id: "b", first_year: 1990, last_year: 2022 }),
      ]),
    ).toMatchObject({ firstYear: 1983, lastYear: 2022 });
  });
});
