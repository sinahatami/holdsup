import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { HistoryList } from "@/components/organisms/history-list";
import { historyStore } from "@/lib/history";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.history;

beforeEach(() => {
  localStorage.clear();
  act(() => historyStore.clear());
});

describe("HistoryList", () => {
  it("shows nothing before there is a check", () => {
    const { container } = render(<HistoryList />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists a check as a link to its receipt, newest first", () => {
    act(() => {
      historyStore.add("one", "First claim");
      historyStore.add("two", "Second claim");
    });
    render(<HistoryList />);
    expect(screen.getByRole("heading", { name: t.heading })).toBeVisible();
    const links = screen.getAllByRole("link");
    expect(links.map((a) => a.textContent)).toEqual([
      "Second claim",
      "First claim",
    ]);
    expect(links[0]).toHaveAttribute("href", routes.check("two"));
    expect(screen.getAllByText(t.running)).toHaveLength(2);
  });

  it("shows the verdicts once the check has finished", () => {
    act(() => {
      historyStore.add("one", "A claim");
      historyStore.finish("one", ["supported", "not_supported"]);
    });
    render(<HistoryList />);
    expect(screen.getByText(t.summary(1, 2))).toBeVisible();
    expect(screen.queryByText(t.running)).not.toBeInTheDocument();
  });

  it("removes one check, then hides itself when the last goes", () => {
    act(() => historyStore.add("one", "A claim"));
    render(<HistoryList />);
    fireEvent.click(screen.getByRole("button", { name: t.remove("A claim") }));
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });

  it("clears the whole list", () => {
    act(() => {
      historyStore.add("one", "A");
      historyStore.add("two", "B");
    });
    render(<HistoryList />);
    fireEvent.click(screen.getByRole("button", { name: t.clear }));
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(historyStore.getSnapshot()).toEqual([]);
  });
});
