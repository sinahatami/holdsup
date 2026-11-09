import { describe, expect, it } from "vitest";
import type { CheckResult, Label } from "@/lib/api/client";
import {
  clip,
  receiptDescription,
  receiptTitle,
  verdictLine,
} from "@/lib/receipt-meta";

function claim(quote: string, label: Label, explanation = "Because.") {
  return {
    claim: { quote },
    verdict: { label, reason: "Reason." },
    explanation,
  };
}

function result(text: string, ...claims: ReturnType<typeof claim>[]) {
  return { text, claims } as unknown as CheckResult;
}

describe("clip", () => {
  it("collapses whitespace and cuts long text with an ellipsis", () => {
    expect(clip("  a \n  b  ", 10)).toBe("a b");
    expect(clip("abcdefghij", 6)).toBe("abcde…");
    expect(clip("abcdef", 6)).toBe("abcdef");
  });
});

describe("verdictLine", () => {
  it("names the verdict of a single claim", () => {
    expect(verdictLine([{ label: "not_supported" }])).toBe("Does not hold up");
  });

  it("counts the claims that hold up when there are several", () => {
    expect(
      verdictLine([
        { label: "supported" },
        { label: "supported_framing_matters" },
        { label: "not_supported" },
      ]),
    ).toBe("2 of 3 claims hold up");
  });
});

describe("receipt title and description", () => {
  const one = result(
    "Renzi, 2013: debt is 133% of GDP.",
    claim("Debt is 133% of GDP.", "supported", "Debt was 132.6% of GDP."),
  );

  it("leads with the verdict and quotes the claim", () => {
    expect(receiptTitle(one)).toBe("Holds up · “Debt is 133% of GDP.”");
  });

  it("explains a single claim in the description", () => {
    expect(receiptDescription(one)).toBe("Debt was 132.6% of GDP.");
  });

  it("falls back to the verdict's reason when there is no explanation", () => {
    const bare = result("x", claim("Debt is 133%.", "supported", ""));
    expect(receiptDescription(bare)).toBe("Reason.");
  });

  it("uses the whole text and a count when there are several claims", () => {
    const two = result(
      "In 2011 youth unemployment was 29%; today it is 43.3%.",
      claim("youth unemployment was 29%", "supported"),
      claim("today it is 43.3%", "not_supported"),
    );
    expect(receiptTitle(two)).toBe(
      "1 of 2 claims hold up · “In 2011 youth unemployment was 29%; today it is 43.3%.”",
    );
    expect(receiptDescription(two)).toBe(two.text);
  });

  it("keeps a long claim to one short line", () => {
    const long = result("x", claim("a".repeat(300), "supported"));
    expect(receiptTitle(long).length).toBeLessThan(130);
    const many = result(
      "b".repeat(500),
      claim("q", "supported"),
      claim("r", "supported"),
    );
    expect(receiptDescription(many)).toHaveLength(200);
  });
});
