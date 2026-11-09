import { describe, expect, it } from "vitest";
import type { ClaimResult, ClaimSpec, Operation } from "@/lib/api/client";
import {
  annotate,
  claimReading,
  comparison,
  decidingOp,
  framingPercent,
  hasMoreThanQuotes,
  opGloss,
  sourceLinks,
} from "@/lib/receipt";
import {
  checkResult,
  holdingClaim,
  partlyClaim,
  unmatchedClaim,
} from "@/test/fixtures";

const rows = (c: ClaimResult) =>
  Object.fromEntries(claimReading(c.claim).map((r) => [r.label, r]));

describe("claimReading", () => {
  it("lists what was understood, with names and words instead of codes", () => {
    const r = rows(holdingClaim);
    expect(r["Statistic"].value).toBe("unemployment rate");
    expect(r["Place"].value).toBe("Italy");
    expect(r["Period"].value).toBe("2015 to 2023");
    expect(r["Kind of claim"].value).toBe("A change in percentage points");
    expect(r["Direction"].value).toBe("Down");
    expect(r["From, to"].value).toBe("11.9 → 7.7");
    // Nothing stated for these, so no row.
    expect(r["Figure stated"]).toBeUndefined();
    expect(r["Said by"]).toBeUndefined();
    expect(r["Compared with"]).toBeUndefined();
  });

  it("says when a value was inferred or taken from a term of office", () => {
    const r = rows(partlyClaim);
    expect(r["Place"]).toMatchObject({
      value: "Italy",
      note: "inferred from the context",
    });
    expect(r["Period"]).toMatchObject({
      value: "February 2014 to the latest period",
      note: "start: taken from the speaker's term of office",
    });
    expect(r["Figure stated"].value).toBe("12 points");
    expect(r["Said by"].value).toBe("Renzi, 2018");
  });

  it("says a shared reason once, and shows no note for stated values", () => {
    const spec: ClaimSpec = {
      ...holdingClaim.claim,
      start_basis: "assumed",
      end_basis: "assumed",
    };
    expect(claimReading(spec).find((r) => r.label === "Period")?.note).toBe(
      "assumed, because the claim says “for years” or “recently”",
    );
    const plain = claimReading(holdingClaim.claim).find(
      (r) => r.label === "Period",
    );
    expect(plain?.note).toBeUndefined();
  });

  it("names peers and writes a bound with its word", () => {
    const spec: ClaimSpec = {
      ...holdingClaim.claim,
      peers: ["FR", "DE"],
      assertion: {
        ...holdingClaim.claim.assertion,
        value: 18,
        unit: "%",
        operator: "more_than",
        start_value: null,
        end_value: null,
      },
    };
    const r = Object.fromEntries(
      claimReading(spec).map((x) => [x.label, x.value]),
    );
    expect(r["Compared with"]).toBe("France, Germany");
    expect(r["Figure stated"]).toBe("more than 18%");
    expect(r["From, to"]).toBeUndefined();
  });

  it("starts or ends at a single stated value", () => {
    const withEnd = {
      ...holdingClaim.claim,
      assertion: {
        ...holdingClaim.claim.assertion,
        start_value: null,
        end_value: 7.7,
      },
    };
    expect(rows({ ...holdingClaim, claim: withEnd })["Ends at"].value).toBe(
      "7.7",
    );
  });
});

describe("comparison", () => {
  it("sets each stated figure beside the official one, with the gap allowed", () => {
    const [claim, start, end] = comparison(holdingClaim);
    // The claim only says "down": a direction, with no figure to hold it to.
    expect(claim).toMatchObject({
      label: "The claim itself",
      holds: true,
      claimed: "down",
      official: "-4.34 points",
      gap: null,
      note: "Only the direction is compared.",
    });
    expect(start).toMatchObject({
      label: "Start value",
      period: "2015",
      holds: true,
      claimed: "11.9%",
      official: "12.02%",
      gap: "±0.17%",
      note: null,
    });
    expect(end).toMatchObject({
      label: "End value",
      claimed: "7.7%",
      official: "7.68%",
      gap: "±0.13%",
    });
  });

  it("marks the parts that do not hold, with the claim's own figure in the claim's unit", () => {
    const [claim, start, end] = comparison(partlyClaim);
    expect(claim).toMatchObject({
      holds: false,
      claimed: "-12 points",
      official: "-10.7 points",
      gap: "±0.5 points",
    });
    expect(start).toMatchObject({ holds: false, period: "February 2014" });
    expect(end).toMatchObject({ holds: true, period: "November 2018" });
  });

  it("gives a bound no gap, and names the word that bounds it", () => {
    const bound: ClaimResult = {
      ...partlyClaim,
      verdict: {
        ...partlyClaim.verdict,
        parts: [
          {
            name: "assertion",
            holds: true,
            computed: -20,
            asserted: -18,
            tolerance: 0.5,
            operator: "more_than",
            detail: "",
          },
        ],
      },
    };
    expect(comparison(bound)[0]).toMatchObject({
      claimed: "more than -18 points",
      gap: null,
    });
  });

  it("names the place a claim was set against", () => {
    const peers: ClaimResult = {
      ...partlyClaim,
      verdict: {
        ...partlyClaim.verdict,
        parts: [
          {
            name: "vs FR",
            holds: true,
            computed: 2.1,
            operator: "about",
            detail: "difference in change 2.1; claim says down",
          },
        ],
      },
    };
    expect(comparison(peers)[0]).toMatchObject({
      label: "Against France",
      official: "2.1",
    });
  });

  it("is empty when nothing was compared", () => {
    expect(comparison(unmatchedClaim)).toEqual([]);
  });
});

describe("decidingOp", () => {
  it("is the operation the plan named, if any", () => {
    expect(decidingOp(holdingClaim)?.op).toBe("change");
    expect(decidingOp(unmatchedClaim)).toBeUndefined();
  });
});

describe("sourceLinks", () => {
  it("links the matched series and any series used besides it", () => {
    expect(sourceLinks(holdingClaim)).toEqual([
      { label: "Eurostat une_rt_m", url: holdingClaim.data?.url },
    ]);
    const extra = {
      indicator: holdingClaim.indicator!,
      data: { ...holdingClaim.data!, dataset: "demo_pjan", url: "https://p" },
    };
    expect(
      sourceLinks({ ...holdingClaim, extra_sources: [extra] }).map(
        (l) => l.label,
      ),
    ).toEqual(["Eurostat une_rt_m", "Eurostat demo_pjan"]);
  });

  it("has none when no data was fetched", () => {
    expect(sourceLinks(unmatchedClaim)).toEqual([]);
  });
});

describe("opGloss", () => {
  const op = (name: string, args: Operation["args"]): Operation => ({
    op: name,
    args,
    inputs: [],
  });

  it.each([
    [
      op("value_at", { geo: "IT", period: "2014-02" }),
      "Look up the value for Italy in February 2014.",
    ],
    [
      op("change", { start: "2015", end: "2023", kind: "percentage_points" }),
      "Take the rate for 2015 away from the rate for 2023.",
    ],
    [
      op("change", { start: "2015", end: "latest", kind: "percent" }),
      "Take the value for 2015 away from the value for the latest period, divide by the value for 2015, and multiply by 100.",
    ],
    [
      op("change", { start: "2015", end: "2023", kind: "ratio" }),
      "Divide the value for 2023 by the value for 2015.",
    ],
    [
      op("cagr", { start: "2015", end: "2023" }),
      "Work out the yearly growth rate that takes the value from 2015 to 2023.",
    ],
    [
      op("trend", { start: "2015", end: "2023" }),
      "Fit a straight line through the values from 2015 to 2023 and read its slope per year.",
    ],
    [
      op("compare", { geo: "IT", geo_b: "FR", period: "2023" }),
      "Take the value for France away from the value for Italy in 2023.",
    ],
    [
      op("rank", { geo: "IT", geos: ["FR", "DE"], period: "2023" }),
      "Order the places by their value in 2023 and find the position of Italy.",
    ],
    [
      op("per_capita", { geo: "IT", scale: 1 }),
      "Divide each value by the population for the same period.",
    ],
    [
      op("deflate", { geo: "IT", base: "2020" }),
      "Restate each value in the prices of 2020, using the price index.",
    ],
  ])("puts %j in words", (operation, words) => {
    expect(opGloss(operation)).toBe(words);
  });

  it("says nothing about a call it cannot put in words", () => {
    expect(opGloss(op("mystery", {}))).toBeNull();
    expect(opGloss(op("value_at", { geo: "IT" }))).toBeNull();
    expect(opGloss(op("change", { start: "2015", end: "2023" }))).toBeNull();
    expect(
      opGloss(op("change", { start: "2015", end: "2023", kind: "odd" })),
    ).toBeNull();
  });
});

describe("annotate", () => {
  const text = "In 2011 youth unemployment was 29%; today it is 43.3%.";

  it("splits the text at each claim's quote, in the order they were said", () => {
    expect(
      annotate(text, ["today it is 43.3%.", "youth unemployment was 29%"]),
    ).toEqual([
      { text: "In 2011 ", claim: null },
      { text: "youth unemployment was 29%", claim: 1 },
      { text: "; ", claim: null },
      { text: "today it is 43.3%.", claim: 0 },
    ]);
  });

  it("finds a quote that differs from the text only by case", () => {
    expect(annotate("Debt IS 133%.", ["debt is 133%."])).toEqual([
      { text: "Debt IS 133%.", claim: 0 },
    ]);
  });

  it("finds a quote written with straight quotes where the text has curly ones", () => {
    expect(
      annotate("Italy\u2019s debt is 133%.", ["Italy's debt is 133%."]),
    ).toEqual([{ text: "Italy\u2019s debt is 133%.", claim: 0 }]);
  });

  it("finds a quote whose closing punctuation differs from the text's", () => {
    expect(
      annotate("Youth unemployment was 29%; today it is 43.3%.", [
        "Youth unemployment was 29%.",
        "today it is 43.3%.",
      ]),
    ).toEqual([
      { text: "Youth unemployment was 29%", claim: 0 },
      { text: "; ", claim: null },
      { text: "today it is 43.3%.", claim: 1 },
    ]);
  });

  it("leaves a quote it cannot find unmarked, and keeps the first of two that overlap", () => {
    expect(annotate("Debt is 133%.", ["nothing like it"])).toEqual([
      { text: "Debt is 133%.", claim: null },
    ]);
    expect(annotate("abcdef", ["abcd", "cdef"])).toEqual([
      { text: "abcd", claim: 0 },
      { text: "ef", claim: null },
    ]);
  });

  it("is one unmarked stretch when there are no quotes, and nothing when there is no text", () => {
    expect(annotate("hello", [])).toEqual([{ text: "hello", claim: null }]);
    expect(annotate("", ["x"])).toEqual([]);
  });
});

describe("hasMoreThanQuotes", () => {
  it("is false when the text is just the claim, however it is spaced", () => {
    expect(hasMoreThanQuotes("Debt is 133%.", ["Debt is 133%."])).toBe(false);
    expect(hasMoreThanQuotes(" Debt  is\n133%. ", ["Debt is 133%."])).toBe(
      false,
    );
  });
  it("is true for words around the claim, and for several claims", () => {
    expect(
      hasMoreThanQuotes("Renzi, 2013: Debt is 133%.", ["Debt is 133%."]),
    ).toBe(true);
    expect(hasMoreThanQuotes("A 5%. B 6%.", ["A 5%.", "B 6%."])).toBe(true);
  });
  it("is false when there is no claim", () => {
    expect(hasMoreThanQuotes("nothing", [])).toBe(false);
  });
});

describe("framingPercent", () => {
  it("is the threshold the result recorded, as a whole percent", () => {
    expect(framingPercent(checkResult([holdingClaim]))).toBe(70);
  });
  it("looks past a claim that could not be checked", () => {
    expect(framingPercent(checkResult([unmatchedClaim, holdingClaim]))).toBe(
      70,
    );
  });
  it("is null when no claim has one", () => {
    expect(framingPercent(checkResult([unmatchedClaim]))).toBeNull();
  });
});
