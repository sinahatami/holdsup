import type { StepEvent } from "@/lib/api/client";

export type TraceState = "running" | "ok" | "cant_check";

export interface TraceRow {
  key: string;
  step: StepEvent["step"];
  claim: number | null;
  state: TraceState;
  summary: string;
  models: string[];
  ms: number | null;
}

/** Fold one trace event into the rows; rows keep the order steps first appeared. */
export function applyStep(rows: TraceRow[], e: StepEvent): TraceRow[] {
  const key = `${e.claim ?? "all"}:${e.step}`;
  const row: TraceRow = {
    key,
    step: e.step,
    claim: e.claim,
    state: e.event === "step_started" ? "running" : (e.status ?? "ok"),
    summary: e.summary,
    models: e.models,
    ms: e.ms,
  };
  const at = rows.findIndex((r) => r.key === key);
  if (at === -1) return [...rows, row];
  return rows.map((r, i) => (i === at ? row : r));
}
