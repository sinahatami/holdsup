import { describe, expect, it } from "vitest";
import { strings } from "@/lib/strings";
import { changeLines, revisedSummary } from "@/lib/watch";
import { checkResult, holdingClaim, partlyClaim } from "@/test/fixtures";
import { revisedClaim, updateResult } from "@/test/watch";

const t = strings.watch;

describe("revisedSummary", () => {
  const old = checkResult([holdingClaim]);

  it("says when the claim was checked again and what its verdict is now", () => {
    expect(revisedSummary(old, updateResult())).toBe(
      `${t.checkedAgain("December 7, 2026")} ${t.nowIs(strings.verdicts.partly_supported)}`,
    );
  });

  it("says a verdict still stands when only the figures moved", () => {
    expect(revisedSummary(old, updateResult([holdingClaim]))).toBe(
      `${t.checkedAgain("December 7, 2026")} ${t.stands}`,
    );
  });

  it("counts the verdicts that changed among several claims", () => {
    const two = checkResult([holdingClaim, { ...holdingClaim, index: 1 }]);
    const after = updateResult([revisedClaim, { ...holdingClaim, index: 1 }]);
    expect(revisedSummary(two, after)).toContain(t.changed(1, 2));
    expect(
      revisedSummary(
        two,
        updateResult([holdingClaim, { ...holdingClaim, index: 1 }]),
      ),
    ).toContain(t.allStand);
  });
});

describe("changeLines", () => {
  it("gives each figure that moved, named and in its unit, with the verdict before", () => {
    expect(changeLines(updateResult())).toEqual([
      "It was “Holds up”. The claim itself: from -4.34 points to -2.84 points; End value, 2023: from 7.68% to 9.18%.",
    ]);
  });

  it("numbers the claims of a check with several, and says when only a framing check moved", () => {
    const update = updateResult([holdingClaim, { ...partlyClaim, index: 1 }]);
    const [change] = update.update_of?.changes ?? [];
    if (!change) throw new Error("the fixture has a change");
    const framing = { ...change, index: 1, figures: [] };
    const lines = changeLines({
      ...update,
      update_of: update.update_of && {
        ...update.update_of,
        changes: [change, framing],
      },
    });
    expect(lines[0]).toMatch(/^Claim 1 was “Holds up”\. The claim itself/);
    expect(lines[1]).toBe(`Claim 2 was “Holds up”. ${t.framingOnly}`);
  });

  it("is empty for a check the watch did not make", () => {
    expect(changeLines(checkResult([holdingClaim]))).toEqual([]);
  });
});
