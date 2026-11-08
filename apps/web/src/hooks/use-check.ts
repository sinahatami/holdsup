"use client";

import { useEffect, useState } from "react";
import {
  browserApi,
  toProblem,
  type ApiClient,
  type CheckResult,
  type Problem,
} from "@/lib/api/client";
import { applyStep, type TraceRow } from "@/lib/trace";

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

/** Loads a check, and follows its live trace while it is still running. */
export function useCheck(id: string, api: ApiClient = browserApi): CheckState {
  const [state, setState] = useState<CheckState>(initial);

  useEffect(() => {
    let stop: (() => void) | undefined;
    let cancelled = false;

    const patch = (part: Partial<CheckState>) =>
      setState((s) => ({ ...s, ...part }));
    const fail = (problem: Problem) =>
      patch({ loading: false, error: problem });

    api
      .getCheck(id)
      .then((view) => {
        if (cancelled) return;
        if (view.result) return patch({ loading: false, result: view.result });
        if (view.status === "failed" && view.error) return fail(view.error);

        patch({ loading: false });
        stop = api.follow(id, {
          onStep: (e) =>
            setState((s) => ({ ...s, trace: applyStep(s.trace, e) })),
          onResult: (result) => patch({ result }),
          onProblem: fail,
          onConnectionLost: () => patch({ connectionLost: true }),
        });
      })
      .catch((err: unknown) => {
        if (!cancelled) fail(toProblem(err));
      });

    return () => {
      cancelled = true;
      stop?.();
    };
  }, [id, api]);

  return state;
}
