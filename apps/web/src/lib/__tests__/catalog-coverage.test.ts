import { describe, expect, it } from "vitest";
import { coverageText } from "@/lib/catalog-coverage";
import { catalogEntry } from "@/test/fixtures";

const entry = (over: Parameters<typeof catalogEntry>[0]) => catalogEntry(over);

describe("coverageText", () => {
  it("counts countries when there are many, and names the group", () => {
    const countries = Array.from({ length: 30 }, (_, i) => `C${i}`);
    expect(coverageText(entry({ id: "a", countries, groups: ["EU"] }))).toBe(
      "30 countries and the EU as a whole",
    );
  });

  it("names a few countries", () => {
    expect(
      coverageText(entry({ id: "a", countries: ["IT", "NO"], groups: [] })),
    ).toBe("Italy and Norway");
  });

  it("says every country, and the world as a whole", () => {
    expect(
      coverageText(
        entry({
          id: "a",
          countries: [],
          groups: ["WORLD"],
          all_countries: true,
        }),
      ),
    ).toBe("Every country and the world as a whole");
  });

  it("falls back to the place's name for a group it has no phrase for", () => {
    expect(
      coverageText(entry({ id: "a", countries: [], groups: ["G7"] })),
    ).toBe("G7");
  });
});
