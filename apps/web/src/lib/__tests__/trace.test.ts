import { describe, expect, it } from "vitest";
import type { StepEvent } from "@/lib/api/client";
import { applyStep } from "@/lib/trace";

const ev = (over: Partial<StepEvent>): StepEvent => ({
  event: "step_started",
  step: "extract",
  claim: null,
  status: null,
  summary: "",
  models: [],
  ms: null,
  ...over,
});

describe("applyStep", () => {
  it("adds a running row, then completes it in place", () => {
    let rows = applyStep([], ev({}));
    rows = applyStep(rows, ev({ step: "match", claim: 0 }));
    expect(rows.map((r) => r.state)).toEqual(["running", "running"]);
    rows = applyStep(
      rows,
      ev({ event: "step_done", status: "ok", summary: "1 claim", ms: 5 }),
    );
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ state: "ok", summary: "1 claim" });
  });

  it("keeps cant_check and keys rows by claim", () => {
    let rows = applyStep([], ev({ step: "match", claim: 0 }));
    rows = applyStep(rows, ev({ step: "match", claim: 1 }));
    rows = applyStep(
      rows,
      ev({ event: "step_done", step: "match", claim: 1, status: "cant_check" }),
    );
    expect(rows.map((r) => r.state)).toEqual(["running", "cant_check"]);
  });
});
