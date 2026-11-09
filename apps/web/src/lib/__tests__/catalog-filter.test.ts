import { describe, expect, it } from "vitest";
import {
  filterCatalog,
  filterQuery,
  isFiltered,
  noFilter,
  placeOptions,
  readFilter,
  yearSpan,
  yearsBackwards,
} from "@/lib/catalog-filter";
import { catalogEntry } from "@/test/fixtures";

const rent = catalogEntry({
  id: "rent",
  name: "Rent prices (Eurostat)",
  theme: "prices",
  definition: "How much tenants pay.",
  aliases: ["cost of renting a home"],
  first_year: 2005,
  last_year: 2022,
});
const unemployment = catalogEntry({
  id: "unemployment",
  name: "Unemployment rate (World Bank)",
  theme: "work",
  source: "the World Bank",
  source_code: "SL.UEM.TOTL.ZS",
  countries: [],
  groups: ["WORLD"],
  all_countries: true,
  first_year: 1991,
});
const poverty = catalogEntry({
  id: "poverty",
  name: "At-risk-of-poverty rate",
  theme: "poverty",
  countries: ["IT", "NO"],
  groups: ["EU"],
  first_year: 1995,
});
const all = [rent, unemployment, poverty];
const ids = (f: Partial<typeof noFilter>) =>
  filterCatalog(all, { ...noFilter, ...f }).map((e) => e.id);

describe("filterCatalog", () => {
  it("returns everything when nothing is asked", () => {
    expect(ids({})).toEqual(["rent", "unemployment", "poverty"]);
    expect(isFiltered(noFilter)).toBe(false);
  });

  it("finds words in the name, the definition, an alias, the source and its code", () => {
    expect(ids({ q: "rent" })).toEqual(["rent"]);
    expect(ids({ q: "tenants" })).toEqual(["rent"]);
    expect(ids({ q: "renting" })).toEqual(["rent"]);
    expect(ids({ q: "world bank" })).toEqual(["unemployment"]);
    expect(ids({ q: "sl.uem" })).toEqual(["unemployment"]);
  });

  it("needs every word, ignores case and accents, and ignores stray spaces", () => {
    expect(ids({ q: "  RATE   poverty " })).toEqual(["poverty"]);
    expect(ids({ q: "rate rent" })).toEqual([]);
    expect(ids({ q: "Rént" })).toEqual(["rent"]);
  });

  it("narrows by topic", () => {
    expect(ids({ theme: "work" })).toEqual(["unemployment"]);
  });

  it("narrows by a country: those that name it, and those that cover every country", () => {
    expect(ids({ place: "IT" })).toEqual(["rent", "unemployment", "poverty"]);
    expect(ids({ place: "NO" })).toEqual(["unemployment", "poverty"]);
    // Brazil is named nowhere, but a worldwide series covers it.
    expect(ids({ place: "BR" })).toEqual(["unemployment"]);
  });

  it("narrows by a group only where the group is named", () => {
    expect(ids({ place: "EU" })).toEqual(["rent", "poverty"]);
    expect(ids({ place: "WORLD" })).toEqual(["unemployment"]);
  });

  it("keeps a series that reaches into the years asked, and one still being updated", () => {
    expect(ids({ from: 2023 })).toEqual(["unemployment", "poverty"]);
    expect(ids({ to: 1994 })).toEqual(["unemployment"]);
    expect(ids({ from: 2010, to: 2015 })).toEqual([
      "rent",
      "unemployment",
      "poverty",
    ]);
  });

  it("matches nothing when the years run backwards", () => {
    const f = { ...noFilter, from: 2020, to: 2010 };
    expect(yearsBackwards(f)).toBe(true);
    expect(filterCatalog(all, f)).toEqual([]);
  });

  it("applies every part together", () => {
    expect(
      ids({ q: "rate", place: "NO", theme: "poverty", from: 2000 }),
    ).toEqual(["poverty"]);
    expect(ids({ q: "rate", theme: "prices" })).toEqual([]);
  });

  it("can leave the topic out, to count how many each topic would give", () => {
    const f = { ...noFilter, theme: "work" as const, place: "NO" };
    expect(filterCatalog(all, f, "theme").map((e) => e.id)).toEqual([
      "unemployment",
      "poverty",
    ]);
  });
});

describe("placeOptions and yearSpan", () => {
  it("lists the groups and countries the catalog names, once each", () => {
    expect(placeOptions(all)).toEqual({
      groups: ["EU", "WORLD"],
      countries: ["DE", "FR", "IT", "NO"],
    });
  });

  it("spans the years, open at the end while a series is updated", () => {
    expect(yearSpan(all)).toEqual({ first: 1991, last: null });
    expect(yearSpan([rent])).toEqual({ first: 2005, last: 2022 });
    expect(yearSpan([])).toBeNull();
  });
});

describe("the filter in an address", () => {
  const themes = ["work", "prices"];

  it("round-trips", () => {
    const f = {
      q: "rent prices",
      theme: "prices" as const,
      place: "IT",
      from: 2010,
      to: 2020,
    };
    const query = filterQuery(f);
    expect(readFilter(new URLSearchParams(query), themes)).toEqual(f);
  });

  it("writes nothing for an empty filter", () => {
    expect(filterQuery(noFilter)).toBe("");
    expect(filterQuery({ ...noFilter, q: "   " })).toBe("");
  });

  it("ignores values that cannot be right", () => {
    const f = readFilter(
      new URLSearchParams("theme=weather&place=it&from=20&to=abcd"),
      themes,
    );
    expect(f).toEqual(noFilter);
  });
});
