import { act, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CheckReport } from "@/components/organisms/check-report";
import type { CheckState } from "@/hooks/use-check";
import { strings } from "@/lib/strings";
import type { TraceRow } from "@/lib/trace";
import { checkResult, holdingClaim } from "@/test/fixtures";

// A checked claim offers re-checks, which open the new check with the router.
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

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

// jsdom has neither; the result of a followed check scrolls itself into view.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  window.matchMedia = vi.fn().mockReturnValue({ matches: false });
});

describe("the progress of a check being followed", () => {
  it("is not shown while the check itself is still being loaded", () => {
    render(<CheckReport state={state({ loading: true })} />);
    expect(screen.queryByText(t.heading)).not.toBeInTheDocument();
  });

  it("is stood in for by a placeholder that says it is loading", () => {
    render(<CheckReport state={state({ loading: true })} />);
    expect(screen.getByRole("status")).toHaveTextContent(strings.check.loading);
    // The bars are decorative.
    expect(screen.getByTestId("check-placeholder")).toHaveAttribute(
      "aria-hidden",
    );
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

describe("the time a stage has taken and the line between stages", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("counts the seconds of the running stage only, out of the screen reader's way", () => {
    render(
      <CheckReport
        state={state({
          trace: [
            row({ step: "ledger", state: "ok" }),
            row({ step: "fetch", claim: 0, state: "running" }),
          ],
        })}
      />,
    );
    // Nothing for the first second, so a quick stage shows no number at all.
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.queryByTestId("elapsed")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(11_000));
    const elapsed = screen.getByTestId("elapsed");
    expect(elapsed).toHaveTextContent(t.elapsed(12));
    expect(elapsed).toHaveAttribute("aria-hidden");
    expect(item(t.stages.fetch)).toContainElement(elapsed);
  });

  it("joins each stage to the next, and fills the line from stages behind", () => {
    const { container } = render(
      <CheckReport
        state={state({
          trace: [
            row({ step: "match", claim: 0, state: "ok" }),
            row({ step: "fetch", claim: 0, state: "running" }),
          ],
        })}
      />,
    );
    // Five stages, four lines between them; the fill is keyed on the stage's data-state.
    const lines = container.querySelectorAll(".stage-line");
    expect(lines).toHaveLength(4);
    expect(lines[0].parentElement).toHaveAttribute("data-state", "done");
    expect(lines[1].parentElement).toHaveAttribute("data-state", "running");
  });

  it("writes a long wait in minutes and seconds", () => {
    expect(t.elapsed(59)).toBe("59 s");
    expect(t.elapsed(65)).toBe("1 min 5 s");
  });
});

describe("the result of a check", () => {
  const result = checkResult([holdingClaim]);

  it("is brought into view and focused when it ends a check the reader followed", () => {
    render(
      <CheckReport
        state={state({ trace: [row({ step: "match", claim: 0 })], result })}
      />,
    );
    const region = screen.getByRole("region", {
      name: strings.check.resultLabel,
    });
    expect(region).toHaveFocus();
    expect(region.scrollIntoView).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "start",
    });
  });

  it("jumps without animation when the reader asks for reduced motion", () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    render(
      <CheckReport
        state={state({ trace: [row({ step: "match", claim: 0 })], result })}
      />,
    );
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: "auto",
      block: "start",
    });
  });

  it("is left where it is when the page opened on a finished check", () => {
    render(<CheckReport state={state({ result })} />);
    expect(
      screen.getByRole("region", { name: strings.check.resultLabel }),
    ).not.toHaveFocus();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });
});
