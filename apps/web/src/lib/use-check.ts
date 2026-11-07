"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  getCheck,
  streamUrl,
  type CheckResult,
  type Problem,
  type StepEvent,
} from "@/lib/api/client";

export interface TraceRow {
  key: string;
  step: StepEvent["step"];
  claim: number | null;
  state: "running" | "ok" | "cant_check";
  summary: string;
  models: string[];
  ms: number | null;
}

export interface CheckState {
  loading: boolean;
  trace: TraceRow[];
  result: CheckResult | null;
  error: Problem | null;
  connectionLost: boolean;
}

const initial: CheckState = {
  loading: true,
  trace: [],
  result: null,
  error: null,
  connectionLost: false,
};

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

/** Loads a check, and follows its live trace while it is still running. */
export function useCheck(id: string): CheckState {
  const [state, setState] = useState<CheckState>(initial);

  useEffect(() => {
    let source: EventSource | undefined;
    let cancelled = false;

    const fail = (problem: Problem) =>
      setState((s) => ({ ...s, loading: false, error: problem }));

    getCheck(id)
      .then((view) => {
        if (cancelled) return;
        if (view.result) {
          setState((s) => ({
            ...s,
            loading: false,
            result: view.result ?? null,
          }));
          return;
        }
        if (view.status === "failed" && view.error) return fail(view.error);

        setState((s) => ({ ...s, loading: false }));
        source = new EventSource(streamUrl(id));
        const parse = <T>(e: MessageEvent<string>) => JSON.parse(e.data) as T;
        const onStep = (e: MessageEvent<string>) =>
          setState((s) => ({
            ...s,
            trace: applyStep(s.trace, parse<StepEvent>(e)),
          }));
        source.addEventListener("step_started", onStep);
        source.addEventListener("step_done", onStep);
        source.addEventListener("result", (e) => {
          setState((s) => ({ ...s, result: parse<CheckResult>(e) }));
          source?.close();
        });
        source.addEventListener("error", (e) => {
          if (e instanceof MessageEvent) {
            fail(parse<Problem>(e));
            source?.close();
          } else if (source?.readyState === EventSource.CLOSED) {
            setState((s) => ({ ...s, connectionLost: true }));
          }
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) fail(err.problem);
        else fail({ type: "about:blank", title: "Network error", status: 0 });
      });

    return () => {
      cancelled = true;
      source?.close();
    };
  }, [id]);

  return state;
}
