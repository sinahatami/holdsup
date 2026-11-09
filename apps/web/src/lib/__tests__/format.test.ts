import { describe, expect, it } from "vitest";
import { formatFigures, sourceName } from "@/lib/format";

describe("formatFigures", () => {
  it.each([
    // A short unit goes on both numbers.
    [133.6, 132.6, "% of GDP", "133.6%", "132.6%"],
    [7.7, 7.68, "%", "7.7%", "7.68%"],
    [60, 7.196, "% of labour force aged 15-74", "60%", "7.2%"],
    [
      -12,
      -10.700000000000003,
      "percentage points",
      "-12 points",
      "-10.7 points",
    ],
    [2, 1.931, "×", "2×", "1.93×"],
    // A long unit is said once, after the official number.
    [1.18, 1.18, "live births per woman", "1.18", "1.18 live births per woman"],
    [1234.5, 1234.567, "million euro", "1,234.5", "1,234.57 million euro"],
    // "% per year" keeps its "%" on both.
    [3, 3.21, "% per year", "3%", "3.21% per year"],
    // No unit: bare numbers.
    [4, 4.2, null, "4", "4.2"],
    [4, 4.2, undefined, "4", "4.2"],
    [0.1, 0.123456, "%", "0.1%", "0.12%"],
  ])("writes %s and %s (%s) as %s and %s", (claimed, official, unit, a, b) => {
    expect(formatFigures(claimed, official, unit)).toEqual({
      claimed: a,
      official: b,
    });
  });
});

describe("sourceName", () => {
  it("names the API's source ids", () => {
    expect(sourceName("eurostat")).toBe("Eurostat");
    expect(sourceName("worldbank")).toBe("World Bank");
    expect(sourceName("owid")).toBe("Our World in Data");
  });
  it("drops the article the catalog puts in front of a label", () => {
    expect(sourceName("the World Bank")).toBe("World Bank");
    expect(sourceName("Eurostat")).toBe("Eurostat");
  });
  it("shows an unknown source as it is", () => {
    expect(sourceName("istat")).toBe("istat");
  });
});
