import { describe, expect, it } from "vitest";
import {
  filterRecent,
  isRecentFiltered,
  noRecentFilter,
  readRecentFilter,
  recentPlaces,
  recentQuery,
} from "@/lib/recent-filter";
import { galleryClaim, galleryItem } from "@/test/fixtures";

const italyWork = galleryItem({ id: "a" });
const franceHealth = galleryItem({
  id: "b",
  claims: [
    galleryClaim({
      label: "not_supported",
      geo: "FR",
      theme: "health",
      indicator: "Life expectancy",
    }),
  ],
});
const mixed = galleryItem({
  id: "c",
  claims: [
    galleryClaim({ label: "supported", geo: "DE", theme: "work" }),
    galleryClaim({ label: "partly_supported", geo: "EU", theme: "economy" }),
  ],
});
const unmatched = galleryItem({
  id: "d",
  claims: [
    galleryClaim({
      label: "cant_check",
      geo: null,
      theme: null,
      indicator: null,
      claimed: null,
      official: null,
    }),
  ],
});
const all = [italyWork, franceHealth, mixed, unmatched];
const ids = (f: Partial<typeof noRecentFilter>, skip?: "verdict" | "theme") =>
  filterRecent(all, { ...noRecentFilter, ...f }, skip).map((i) => i.id);

describe("filterRecent", () => {
  it("returns everything, in order, when nothing is asked", () => {
    expect(ids({})).toEqual(["a", "b", "c", "d"]);
    expect(isRecentFiltered(noRecentFilter)).toBe(false);
  });

  it("narrows by verdict, matching a check when any of its claims has it", () => {
    expect(ids({ verdict: "supported" })).toEqual(["a", "c"]);
    expect(ids({ verdict: "partly_supported" })).toEqual(["c"]);
    expect(ids({ verdict: "cant_check" })).toEqual(["d"]);
  });

  it("narrows by place and by topic", () => {
    expect(ids({ place: "FR" })).toEqual(["b"]);
    expect(ids({ place: "EU" })).toEqual(["c"]);
    expect(ids({ theme: "work" })).toEqual(["a", "c"]);
    expect(ids({ theme: "economy" })).toEqual(["c"]);
  });

  it("applies every part together, and a claim must match the same part for each", () => {
    expect(ids({ verdict: "supported", theme: "work", place: "DE" })).toEqual([
      "c",
    ]);
    expect(ids({ verdict: "supported", place: "FR" })).toEqual([]);
  });

  it("can leave a part out, to count what each choice would give", () => {
    expect(ids({ verdict: "not_supported", theme: "work" }, "verdict")).toEqual(
      ["a", "c"],
    );
    expect(ids({ verdict: "supported", theme: "health" }, "theme")).toEqual([
      "a",
      "c",
    ]);
  });
});

describe("recentPlaces", () => {
  it("lists each place the checks are about once, and skips claims with none", () => {
    expect(recentPlaces(all)).toEqual(["IT", "FR", "DE", "EU"]);
    expect(recentPlaces([])).toEqual([]);
  });
});

describe("the filter in an address", () => {
  const verdicts = ["supported", "not_supported"];
  const themes = ["work", "health"];

  it("round-trips", () => {
    const f = {
      verdict: "supported" as const,
      place: "IT",
      theme: "work" as const,
    };
    expect(
      readRecentFilter(new URLSearchParams(recentQuery(f)), verdicts, themes),
    ).toEqual(f);
  });

  it("writes nothing for an empty filter", () => {
    expect(recentQuery(noRecentFilter)).toBe("");
  });

  it("ignores values that cannot be right", () => {
    expect(
      readRecentFilter(
        new URLSearchParams("verdict=great&theme=weather&place=it"),
        verdicts,
        themes,
      ),
    ).toEqual(noRecentFilter);
  });
});
