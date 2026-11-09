import { describe, expect, it } from "vitest";
import type { Step, StepEvent } from "@/lib/api/client";
import { progressOf, type StageState } from "@/lib/progress";
import { applyStep, type TraceRow } from "@/lib/trace";

const started = (step: Step, claim: number | null = null): StepEvent => ({
  event: "step_started",
  step,
  claim,
  status: null,
  summary: "",
  models: [],
  ms: null,
});
const done = (
  step: Step,
  claim: number | null = null,
  status: "ok" | "cant_check" = "ok",
): StepEvent => ({
  ...started(step, claim),
  event: "step_done",
  status,
  ms: 5,
});

const trace = (...events: StepEvent[]): TraceRow[] =>
  events.reduce(applyStep as (r: TraceRow[], e: StepEvent) => TraceRow[], []);

const live = { finished: false, stopped: false };
const states = (rows: TraceRow[], opts = live): StageState[] =>
  progressOf(rows, opts).map((s) => s.state);

describe("progressOf", () => {
  it("lists the stages in order, with the finish last", () => {
    expect(progressOf([], live).map((s) => s.id)).toEqual([
      "find",
      "fetch",
      "recompute",
      "explain",
      "done",
    ]);
  });

  it("has nothing under way before the server has said anything", () => {
    expect(states([])).toEqual([
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ]);
  });

  it("runs a stage only while one of its steps runs", () => {
    expect(states(trace(started("ledger")))).toEqual([
      "running",
      "pending",
      "pending",
      "pending",
      "pending",
    ]);
  });

  it("moves on as each stage's steps finish, never ahead of the server", () => {
    const rows = trace(
      started("ledger"),
      done("ledger"),
      started("extract"),
      done("extract"),
      started("match", 0),
      done("match", 0),
      started("fetch", 0),
    );
    expect(states(rows)).toEqual([
      "done",
      "running",
      "pending",
      "pending",
      "pending",
    ]);
  });

  it("holds the three recomputing steps in one stage", () => {
    const rows = trace(
      started("match", 0),
      done("match", 0),
      started("fetch", 0),
      done("fetch", 0),
      started("plan", 0),
      done("plan", 0),
      started("execute", 0),
    );
    expect(states(rows).slice(0, 3)).toEqual(["done", "done", "running"]);
  });

  it("is running while any claim's step is, and done once all have finished", () => {
    const first = trace(
      started("fetch", 0),
      started("fetch", 1),
      done("fetch", 0),
    );
    expect(states(first)[1]).toBe("running");
    const both = trace(
      started("fetch", 0),
      started("fetch", 1),
      done("fetch", 0),
      done("fetch", 1),
    );
    expect(states(both)[1]).toBe("done");
  });

  it("marks a stage stopped when every claim in it could not be checked", () => {
    const rows = trace(started("match", 0), done("match", 0, "cant_check"));
    expect(states(rows, { finished: true, stopped: false })).toEqual([
      "stopped",
      "skipped",
      "skipped",
      "skipped",
      "done",
    ]);
  });

  it("calls a stage done when only some claims in it were stopped", () => {
    const rows = trace(
      started("match", 0),
      started("match", 1),
      done("match", 0),
      done("match", 1, "cant_check"),
    );
    expect(states(rows)[0]).toBe("done");
  });

  it("does not claim a stage that never ran: an answer from an earlier check skips it", () => {
    const rows = trace(started("ledger"), done("ledger"));
    expect(states(rows, { finished: true, stopped: false })).toEqual([
      "done",
      "skipped",
      "skipped",
      "skipped",
      "done",
    ]);
  });

  it("finishes every stage that ran when the result arrives", () => {
    const rows = trace(
      started("match", 0),
      done("match", 0),
      started("fetch", 0),
      done("fetch", 0),
      started("plan", 0),
      done("plan", 0),
      started("execute", 0),
      done("execute", 0),
      started("verdict", 0),
      done("verdict", 0),
      started("explain", 0),
      done("explain", 0),
    );
    expect(states(rows, { finished: true, stopped: false })).toEqual([
      "done",
      "done",
      "done",
      "done",
      "done",
    ]);
  });

  it("stops the running stage when the check failed or the trace was lost", () => {
    const rows = trace(started("fetch", 0));
    expect(states(rows, { finished: false, stopped: true })).toEqual([
      "pending",
      "stopped",
      "pending",
      "pending",
      "pending",
    ]);
  });
});
