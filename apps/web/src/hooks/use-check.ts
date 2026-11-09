"use client";

import { useEffect, useState } from "react";
import {
  browserApi,
  toProblem,
  type ApiClient,
  type CheckResult,
  type Problem,
} from "@/lib/api/client";
import { historyStore } from "@/lib/history";
import { applyStep, type TraceRow } from "@/lib/trace";

export interface CheckState {
  loading: boolean;
  /** The text that was checked, to send again if the check failed. */
  text: string | null;
  trace: TraceRow[];
  result: CheckResult | null;
  error: Problem | null;
  connectionLost: boolean;
}

const initial: CheckState = {
  loading: true,
  text: null,
  trace: [],
  result: null,
  error: null,
  connectionLost: false,
};

/**
 * Loads a check, and follows its live trace while it is still running. `reconnect` starts
 * again from the check as the server has it, for when the live connection was lost.
 */
export function useCheck(id: string, api: ApiClient = browserApi) {
  const [state, setState] = useState<CheckState>(initial);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let stop: (() => void) | undefined;
    let cancelled = false;

    const patch = (part: Partial<CheckState>) =>
      setState((s) => ({ ...s, ...part }));
    // A check this browser sent remembers how it came out.
    const finish = (result: CheckResult) => {
      historyStore.finish(
        id,
        result.claims.map((c) => c.verdict.label),
      );
      patch({ loading: false, result });
    };
    const fail = (problem: Problem) =>
      patch({ loading: false, error: problem });

    api
      .getCheck(id)
      .then((view) => {
        if (cancelled) return;
        patch({ text: view.text });
        if (view.result) return finish(view.result);
        if (view.status === "failed" && view.error) return fail(view.error);

        patch({ loading: false });
        stop = api.follow(id, {
          onStep: (e) =>
            setState((s) => ({ ...s, trace: applyStep(s.trace, e) })),
          onResult: finish,
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
  }, [id, api, attempt]);

  function reconnect() {
    setState(initial);
    setAttempt((n) => n + 1);
  }

  return { state, reconnect };
}
