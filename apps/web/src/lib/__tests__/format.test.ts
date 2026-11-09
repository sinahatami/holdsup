import { describe, expect, it } from "vitest";
import {
  formatAmount,
  formatDate,
  formatFigures,
  formatPeriod,
  formatTimestamp,
  placeName,
  sourceName,
  withUnit,
} from "@/lib/format";

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

describe("formatAmount", () => {
  it("groups digits and keeps at most two decimals", () => {
    expect(formatAmount(1234.567)).toBe("1,234.57");
    expect(formatAmount(12)).toBe("12");
    expect(formatAmount(-10.700000000000003)).toBe("-10.7");
  });
});

describe("formatPeriod", () => {
  it.each([
    ["2015", "2015"],
    ["2014-02", "February 2014"],
    ["2026-12", "December 2026"],
    ["2025-Q1", "Q1 2025"],
    ["2025-S1", "the first half of 2025"],
    ["2025-S2", "the second half of 2025"],
    ["latest", "the latest period"],
    // Not a period code: shown as it came.
    ["next spring", "next spring"],
  ])("writes %s as %s", (code, words) => {
    expect(formatPeriod(code)).toBe(words);
  });
});

describe("formatTimestamp", () => {
  it("writes a UTC timestamp as a date and a time", () => {
    expect(formatTimestamp("2026-11-07T16:45:30.527958Z")).toBe(
      "November 7, 2026, 16:45 UTC",
    );
  });
  it("reads an offset written without a colon, and converts to UTC", () => {
    expect(formatTimestamp("2026-11-05T23:00:00+0100")).toBe(
      "November 5, 2026, 22:00 UTC",
    );
  });
  it("shows text that is not a date as it came", () => {
    expect(formatTimestamp("yesterday")).toBe("yesterday");
  });
});

describe("formatDate", () => {
  it("writes the UTC day of a timestamp", () => {
    expect(formatDate("2026-11-07T23:59:59Z")).toBe("November 7, 2026");
    expect(formatDate("2026-11-08T00:30:00+0100")).toBe("November 7, 2026");
  });
  it("shows text that is not a date as it came", () => {
    expect(formatDate("soon")).toBe("soon");
  });
});

describe("placeName", () => {
  it("names a country by its code", () => {
    expect(placeName("IT")).toBe("Italy");
    expect(placeName("GB")).toBe("United Kingdom");
  });
  it("names the groups the claim spec uses besides countries", () => {
    expect(placeName("EU")).toBe("European Union");
    expect(placeName("EA")).toBe("Euro area");
    expect(placeName("WORLD")).toBe("World");
  });
  it("shows a code it does not know as it is", () => {
    expect(placeName("NOWHERE")).toBe("NOWHERE");
  });
});

describe("withUnit", () => {
  it("attaches a percent unit to the number and sets other units apart", () => {
    expect(withUnit("42.7", "% of labour force")).toBe("42.7% of labour force");
    expect(withUnit("-4.34", "percentage points")).toBe(
      "-4.34 percentage points",
    );
    expect(withUnit("8", null)).toBe("8");
    expect(withUnit("8", "")).toBe("8");
  });
});
