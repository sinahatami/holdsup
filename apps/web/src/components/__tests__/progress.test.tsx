import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CheckReport } from "@/components/organisms/check-report";
import type { CheckState } from "@/hooks/use-check";
import { strings } from "@/lib/strings";
import type { TraceRow } from "@/lib/trace";
import { checkResult, holdingClaim } from "@/test/fixtures";

const t = strings.progress;

const row = (over: Partial<TraceRow>): TraceRow => ({
  key: `${over.claim ?? "all"}:${over.step ?? "ledger"}`,
  step: "ledger",
  claim: null,
  state: "ok",
  summary: "",
  models: [],
  ms: 5,
  ...over,
});

const state = (over: Partial<CheckState>): CheckState => ({
  loading: false,
  text: null,
  trace: [],
  result: null,
  error: null,
  connectionLost: false,
  ...over,
});

// The trace below names some steps the same way, so look only inside the progress section.
const item = (name: string) =>
  within(screen.getByRole("region", { name: t.heading }))
    .getAllByRole("listitem")
    .find((li) => li.textContent?.startsWith(name))!;

describe("the progress of a check being followed", () => {
  it("is not shown while the check itself is still being loaded", () => {
    render(<CheckReport state={state({ loading: true })} />);
    expect(screen.queryByText(t.heading)).not.toBeInTheDocument();
  });

  it("shows every stage waiting before the first step arrives", () => {
    render(<CheckReport state={state({})} />);
    expect(screen.getByText(t.heading)).toBeInTheDocument();
    for (const label of Object.values(t.stages))
      expect(item(label)).toHaveAttribute("data-state", "pending");
  });

  it("names the stage in progress, for the screen reader too", () => {
    render(
      <CheckReport
        state={state({
          trace: [
            row({ step: "ledger", state: "ok" }),
            row({ step: "match", claim: 0, state: "running" }),
          ],
        })}
      />,
    );
    const finding = item(t.stages.find);
    expect(finding).toHaveAttribute("data-state", "running");
    expect(finding).toHaveAttribute("aria-current", "step");
    expect(finding).toHaveTextContent(`(${t.state.running})`);
    expect(item(t.stages.fetch)).toHaveAttribute("data-state", "pending");
    expect(item(t.stages.done)).toHaveAttribute("data-state", "pending");
  });

  it("ends on Done when the result arrives", () => {
    render(
      <CheckReport
        state={state({
          trace: [
            row({ step: "match", claim: 0 }),
            row({ step: "fetch", claim: 0 }),
          ],
          result: checkResult([holdingClaim]),
        })}
      />,
    );
    expect(item(t.stages.find)).toHaveAttribute("data-state", "done");
    expect(item(t.stages.done)).toHaveAttribute("data-state", "done");
    // Stages the check never ran are not passed off as done.
    expect(item(t.stages.recompute)).toHaveAttribute("data-state", "skipped");
  });

  it("stops the running stage when the check fails", () => {
    render(
      <CheckReport
        state={state({
          trace: [row({ step: "fetch", claim: 0, state: "running" })],
          error: { type: "about:blank", title: "Down", status: 503 },
        })}
      />,
    );
    expect(item(t.stages.fetch)).toHaveAttribute("data-state", "stopped");
  });

  it("is not shown for a check that was read whole, with no trace", () => {
    render(
      <CheckReport state={state({ result: checkResult([holdingClaim]) })} />,
    );
    expect(screen.queryByText(t.heading)).not.toBeInTheDocument();
  });

  it("is not shown for a failed check that never ran anything", () => {
    render(
      <CheckReport
        state={state({
          error: { type: "about:blank", title: "Down", status: 503 },
        })}
      />,
    );
    expect(screen.queryByText(t.heading)).not.toBeInTheDocument();
  });
});
