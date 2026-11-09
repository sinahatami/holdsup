import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "@/lib/clipboard";
import { shareSummary, shareText } from "@/lib/share";
import {
  checkResult,
  holdingClaim,
  partlyClaim,
  unmatchedClaim,
} from "@/test/fixtures";

describe("shareText", () => {
  it("gives a single claim, its verdict and where it was checked", () => {
    expect(shareText(checkResult([holdingClaim]))).toBe(
      "“Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.”\n" +
        "Holds up. Checked with HoldsUp, against Eurostat.",
    );
  });

  it("leaves the source out when nothing was matched", () => {
    expect(shareText(checkResult([unmatchedClaim]))).toBe(
      "“Italy has 20 million people.”\nCan't check. Checked with HoldsUp.",
    );
  });

  it("lists each claim with its own verdict when there are several", () => {
    const text = shareText(
      checkResult([holdingClaim, { ...partlyClaim, index: 1 }]),
    );
    expect(text.split("\n")).toEqual([
      "HoldsUp checked 2 claims: 1 of 2 claims hold up.",
      "1. “Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.” — Holds up",
      "2. “youth unemployment has fallen 12 points, from 44% to 32%.” — Partly holds up",
    ]);
  });

  it("says nothing when there is no claim", () => {
    expect(shareText(checkResult([]))).toBe("");
  });
});

describe("shareSummary", () => {
  it("puts the link on a line of its own after the text", () => {
    expect(shareSummary("Holds up.", "https://holdsup.test/check/1")).toBe(
      "Holds up.\nhttps://holdsup.test/check/1",
    );
  });
});

describe("copyText", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    Reflect.deleteProperty(document, "execCommand");
  });

  it("uses the async clipboard when there is one", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    expect(await copyText("hello")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("hello");
  });

  it("falls back to selecting the text when the async clipboard is missing or refuses", async () => {
    const exec = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", {
      value: exec,
      configurable: true,
    });
    vi.stubGlobal("navigator", {});
    expect(await copyText("hello")).toBe(true);
    expect(exec).toHaveBeenCalledWith("copy");
    // The temporary box is gone again.
    expect(document.querySelector("textarea")).toBeNull();

    vi.stubGlobal("navigator", {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    expect(await copyText("again")).toBe(true);
  });

  it("says it failed when nothing could copy", async () => {
    Object.defineProperty(document, "execCommand", {
      value: vi.fn().mockReturnValue(false),
      configurable: true,
    });
    vi.stubGlobal("navigator", {});
    expect(await copyText("hello")).toBe(false);
    Object.defineProperty(document, "execCommand", {
      value: vi.fn().mockImplementation(() => {
        throw new Error("unsupported");
      }),
      configurable: true,
    });
    expect(await copyText("hello")).toBe(false);
  });
});
