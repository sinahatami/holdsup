import type { Step } from "@/lib/api/client";
import type { TraceRow } from "@/lib/trace";

export type StageId = "find" | "fetch" | "recompute" | "explain" | "done";

/**
 * How far a stage has got. `skipped` is for a stage a finished check never needed (an answer
 * taken from an earlier check fetches nothing); `stopped` for one that could not be completed.
 */
export type StageState = "pending" | "running" | "done" | "stopped" | "skipped";

export interface Stage {
  id: StageId;
  state: StageState;
}

/** The pipeline's steps, grouped into the stages a reader follows. */
const STEPS: Record<Exclude<StageId, "done">, readonly Step[]> = {
  find: ["ledger", "extract", "match"],
  fetch: ["fetch"],
  recompute: ["plan", "execute", "verdict"],
  explain: ["explain"],
};

const ORDER = ["find", "fetch", "recompute", "explain"] as const;

function stateOf(
  rows: readonly TraceRow[],
  finished: boolean,
  stopped: boolean,
): StageState {
  if (rows.some((r) => r.state === "running"))
    return stopped ? "stopped" : "running";
  if (rows.length === 0) return finished ? "skipped" : "pending";
  return rows.some((r) => r.state === "ok") ? "done" : "stopped";
}

/**
 * The stages of a check as far as the live trace says they have got: nothing is timed or
 * guessed, a stage is running only while one of its steps is. `finished` is a result in hand;
 * `stopped` is a check that failed, or whose live trace was lost, before one.
 */
export function progressOf(
  trace: readonly TraceRow[],
  { finished, stopped }: { finished: boolean; stopped: boolean },
): Stage[] {
  const stages = ORDER.map((id) => ({
    id,
    state: stateOf(
      trace.filter((r) => STEPS[id].includes(r.step)),
      finished,
      stopped,
    ),
  }));
  return [...stages, { id: "done", state: finished ? "done" : "pending" }];
}
