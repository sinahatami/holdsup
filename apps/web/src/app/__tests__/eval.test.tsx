import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/eval/page";
import { strings } from "@/lib/strings";
import { benchmarkResponse } from "@/test/fixtures";

const t = strings.benchmark;

function api(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => body }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Eval page", () => {
  it("shows the head-to-head, where HoldsUp loses, every run, the models and the limits", async () => {
    api(benchmarkResponse);
    render(await Page());
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    for (const name of [
      t.headToHead.heading,
      t.losses.heading,
      t.causes.heading,
      t.runs.heading,
      t.models.heading,
      t.limits.heading,
    ]) {
      expect(
        screen.getByRole("heading", { level: 2, name }),
      ).toBeInTheDocument();
    }
    // The limits are on the page, not in a footnote: no web search is the big one.
    expect(screen.getByText(t.limits.items[0])).toBeInTheDocument();
    expect(screen.getByText(t.stamp("0.3.0"))).toBeInTheDocument();
  });

  it("leads with the held-out claims once they have been run", async () => {
    const dev = benchmarkResponse.comparisons[0];
    api({
      ...benchmarkResponse,
      comparisons: [dev, { ...dev, split: "test" }],
    });
    render(await Page());
    const splits = screen
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(splits.slice(0, 2)).toEqual([t.splits.test, t.splits.dev]);
  });

  it("says there is no head-to-head yet, but still shows what the reports hold", async () => {
    api({ ...benchmarkResponse, comparisons: [] });
    render(await Page());
    expect(screen.getByText(t.none)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: t.losses.heading }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: t.runs.heading }),
    ).toBeInTheDocument();
  });

  it("says so when the API is down, and shows no half-page of figures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(await Page());
    expect(screen.getByText(t.down)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: t.headToHead.heading }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Benchmark version/)).not.toBeInTheDocument();
  });
});
