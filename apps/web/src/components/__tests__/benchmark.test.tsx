import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BenchmarkRuns } from "@/components/organisms/benchmark-runs";
import { HeadToHead } from "@/components/organisms/head-to-head";
import { LossList } from "@/components/organisms/loss-list";
import { ModelReports } from "@/components/organisms/model-reports";
import { pageStrings } from "@/lib/strings/pages";
import { benchmarkResponse } from "@/test/fixtures";

const t = pageStrings.benchmark;
const [comparison] = benchmarkResponse.comparisons;

describe("HeadToHead", () => {
  it("sets HoldsUp and the chatbot side by side on the claims both were scored on", () => {
    render(<HeadToHead comparison={comparison} />);
    const table = screen.getByRole("table", {
      name: t.headToHead.caption(t.splits.dev),
    });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(within(rows[0]).getByRole("rowheader")).toHaveTextContent(
      t.who.holdsup,
    );
    expect(rows[0]).toHaveTextContent("75.0%");
    expect(rows[0]).toHaveTextContent("36/48");
    // The chatbot is named by its model, so a reader knows which one HoldsUp is up against.
    expect(rows[1]).toHaveTextContent(t.chatbotOn("GPT-OSS 120B (Groq)"));
    expect(rows[1]).toHaveTextContent("54.2%");
    expect(rows[1]).toHaveTextContent("26/48");
  });

  it("says the development claims are the kind ones, and the held-out ones are not", () => {
    const { rerender } = render(<HeadToHead comparison={comparison} />);
    expect(screen.getByText(t.devNote)).toBeInTheDocument();
    rerender(<HeadToHead comparison={{ ...comparison, split: "test" }} />);
    expect(screen.getByText(t.testNote)).toBeInTheDocument();
    expect(screen.queryByText(t.devNote)).not.toBeInTheDocument();
  });

  it("counts who was right where, and says what was left out of the figures", () => {
    render(<HeadToHead comparison={comparison} />);
    expect(
      screen.getByText(
        "Both right on 24. Only HoldsUp right on 12. Only the chatbot right on 2. Both wrong on 10.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(t.headToHead.leftOut(2, t.who.holdsup)),
    ).toBeInTheDocument();
    // The chatbot left nothing out, so it says nothing.
    expect(screen.queryByText(/Plain chatbot: 0/)).not.toBeInTheDocument();
  });

  it("breaks the accuracy down by the verdict a claim should get", () => {
    render(<HeadToHead comparison={comparison} />);
    const table = screen.getByRole("table", { name: t.byVerdict.caption });
    const framing = within(table)
      .getByRole("rowheader", { name: "Holds up, but the framing matters" })
      .closest("tr");
    expect(framing).toHaveTextContent("50.0% (4 of 8)");
    expect(framing).toHaveTextContent("0.0% (0 of 8)");
    // "No answer" is a column of the matrix, not a verdict a claim should get.
    expect(
      within(table).queryByRole("rowheader", { name: "No answer" }),
    ).not.toBeInTheDocument();
  });

  it("draws the bars for the eye only: the figures carry the meaning", () => {
    const { container } = render(<HeadToHead comparison={comparison} />);
    const bars = container.querySelectorAll("table [aria-hidden='true']");
    expect(bars).toHaveLength(2);
  });
});

describe("LossList", () => {
  it("lists the claims HoldsUp lost, with the step that went wrong", () => {
    render(<LossList comparison={comparison} />);
    const table = screen.getByRole("table", { name: t.losses.caption });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Rents went up 40% in five years");
    expect(rows[0]).toHaveTextContent("Does not hold up");
    expect(rows[0]).toHaveTextContent("Choosing the statistic");
    // A claim the extractor never found has no answer, and the step is reading the claim.
    expect(rows[1]).toHaveTextContent("No answer");
    expect(rows[1]).toHaveTextContent("Reading the claim");
  });

  it("names the three most common causes of a wrong verdict, with their share", () => {
    render(<LossList comparison={comparison} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual([
      "Choosing the statistic: 6 wrong verdicts (50.0%)",
      "Reading the claim: 4 wrong verdicts (33.3%)",
      "Judging the result: 2 wrong verdicts (16.7%)",
    ]);
  });

  it("says so when there is no loss and when there is no wrong verdict", () => {
    render(
      <LossList
        comparison={{
          ...comparison,
          only_chatbot_right: 0,
          losses: [],
          holdsup: { ...comparison.holdsup, failure_causes: [] },
        }}
      />,
    );
    expect(screen.getByText(t.losses.none)).toBeInTheDocument();
    expect(screen.getByText(t.causes.none)).toBeInTheDocument();
  });

  it("says how many losses are shown when the list is cut short", () => {
    render(<LossList comparison={{ ...comparison, only_chatbot_right: 70 }} />);
    expect(screen.getByText(t.losses.more(2, 70))).toBeInTheDocument();
  });
});

describe("BenchmarkRuns", () => {
  it("has a row for every run, with the models that answered and the cost", () => {
    render(<BenchmarkRuns runs={benchmarkResponse.runs} />);
    const rows = within(screen.getByRole("table", { name: t.runs.caption }))
      .getAllByRole("row")
      .slice(1);
    const titles = rows.map((r) => within(r).getByRole("rowheader"));
    expect(titles[0]).toHaveTextContent(/^HoldsUp$/);
    expect(titles[1]).toHaveTextContent(
      /^HoldsUp, GPT-OSS 120B \(Groq\) only$/,
    );
    // A chatbot run says whether it is the one compared above or a weaker model than it.
    expect(titles[2]).toHaveTextContent(
      `Plain chatbot, GPT-OSS 120B (Groq) only${t.runs.roles.compared}`,
    );
    expect(titles[3]).toHaveTextContent(
      `Plain chatbot, Ministral 14B (Mistral) only${t.runs.roles.weaker}`,
    );
    expect(rows[0]).toHaveTextContent(
      "GPT-OSS 120B (Groq), Ministral 14B (Mistral)",
    );
    expect(rows[0]).toHaveTextContent("75.0% (36 of 48)");
    expect(rows[0]).toHaveTextContent("3.2");
    // The chatbot has no pipeline cost per claim: a dash, not zero.
    expect(rows[2]).toHaveTextContent("—");
  });
});

describe("ModelReports", () => {
  it("shows each trained model's table and notes", () => {
    render(<ModelReports reports={benchmarkResponse.models} />);
    expect(
      screen.getByRole("heading", { level: 3, name: "Indicator reranker" }),
    ).toBeInTheDocument();
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows[2]).toHaveTextContent("Fine-tuned reranker94.2%99.0%");
    expect(
      screen.getByText("Cross-validated on the development claims."),
    ).toBeInTheDocument();
  });
});
