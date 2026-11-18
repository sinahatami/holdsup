import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCheck } from "@/hooks/use-check";
import {
  networkProblem,
  type ApiClient,
  type CheckStreamHandlers,
  type CheckView,
  type StepEvent,
} from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { historyStore } from "@/lib/history";
import {
  atCapacityProblem,
  checkResult,
  checkView,
  holdingClaim,
  partlyClaim,
} from "@/test/fixtures";

function fakeApi(view: Promise<CheckView>) {
  let handlers: CheckStreamHandlers | undefined;
  const stop = vi.fn();
  const api = {
    getCheck: vi.fn(() => view),
    follow: vi.fn((_id: string, on: CheckStreamHandlers) => {
      handlers = on;
      return stop;
    }),
  } as unknown as ApiClient;
  return { api, stop, stream: () => handlers! };
}

const step = (over: Partial<StepEvent>): StepEvent => ({
  event: "step_started",
  step: "extract",
  claim: null,
  status: null,
  summary: "",
  models: [],
  ms: null,
  ...over,
});

afterEach(() => historyStore.clear());

describe("useCheck", () => {
  it("shows a finished check and records its verdicts in this browser's history", async () => {
    historyStore.add("c1", "Debt is 133%.");
    const result = checkResult([holdingClaim, partlyClaim]);
    const { api } = fakeApi(
      Promise.resolve(
        checkView({ status: "done", text: "Debt is 133%.", result }),
      ),
    );

    const { result: hook } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(hook.current.state.loading).toBe(false));

    expect(hook.current.state.result).toBe(result);
    expect(hook.current.state.text).toBe("Debt is 133%.");
    expect(api.follow).not.toHaveBeenCalled();
    expect(historyStore.getSnapshot()[0].labels).toEqual([
      shownLabel(holdingClaim),
      shownLabel(partlyClaim),
    ]);
  });

  it("shows the problem of a check that failed", async () => {
    const { api } = fakeApi(
      Promise.resolve(
        checkView({ status: "failed", error: atCapacityProblem }),
      ),
    );

    const { result: hook } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(hook.current.state.loading).toBe(false));

    expect(hook.current.state.error).toEqual(atCapacityProblem);
    expect(api.follow).not.toHaveBeenCalled();
  });

  it("follows a running check's trace until its result arrives", async () => {
    const { api, stream } = fakeApi(
      Promise.resolve(checkView({ status: "running" })),
    );

    const { result: hook } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(api.follow).toHaveBeenCalledTimes(1));
    expect(hook.current.state.loading).toBe(false);

    act(() => stream().onStep(step({ event: "step_started" })));
    expect(hook.current.state.trace).toMatchObject([
      { key: "all:extract", state: "running" },
    ]);
    act(() =>
      stream().onStep(step({ event: "step_done", status: "ok", ms: 120 })),
    );
    expect(hook.current.state.trace).toMatchObject([
      { key: "all:extract", state: "ok", ms: 120 },
    ]);

    const result = checkResult([holdingClaim]);
    act(() => stream().onResult(result));
    expect(hook.current.state.result).toBe(result);
  });

  it("shows a problem the live trace reports", async () => {
    const { api, stream } = fakeApi(
      Promise.resolve(checkView({ status: "running" })),
    );

    const { result: hook } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(api.follow).toHaveBeenCalledTimes(1));
    act(() => stream().onProblem(atCapacityProblem));

    expect(hook.current.state.error).toEqual(atCapacityProblem);
  });

  it("shows a network problem when the check cannot be loaded", async () => {
    const { api } = fakeApi(Promise.reject(new TypeError("Failed to fetch")));

    const { result: hook } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(hook.current.state.loading).toBe(false));

    expect(hook.current.state.error).toEqual(networkProblem());
  });

  it("ignores an answer that arrives after the page has gone", async () => {
    let answer!: (view: CheckView) => void;
    const { api } = fakeApi(new Promise((resolve) => (answer = resolve)));

    const { unmount } = renderHook(() => useCheck("c1", api));
    unmount();
    await act(async () => answer(checkView({ status: "running" })));

    expect(api.follow).not.toHaveBeenCalled();
  });

  it("ignores a failure that arrives after the page has gone", async () => {
    let fail!: (err: unknown) => void;
    const { api } = fakeApi(new Promise((_, reject) => (fail = reject)));

    const { result: hook, unmount } = renderHook(() => useCheck("c1", api));
    unmount();
    await act(async () => fail(new TypeError("Failed to fetch")));

    expect(hook.current.state.error).toBeNull();
  });
});
