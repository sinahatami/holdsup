import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  HISTORY_KEY,
  HISTORY_LIMIT,
  addEntry,
  historyStore,
  parseHistory,
  removeEntry,
  withLabels,
  type HistoryEntry,
} from "@/lib/history";

const entry = (id: string, at = 1): HistoryEntry => ({
  id,
  text: `claim ${id}`,
  at,
});

describe("parseHistory", () => {
  it("reads what was stored", () => {
    const list = [{ ...entry("a"), labels: ["supported", "not_supported"] }];
    expect(parseHistory(JSON.stringify(list))).toEqual(list);
  });

  it.each([null, "", "not json", "{}", "42", "null"])(
    "gives an empty list for %j",
    (raw) => {
      expect(parseHistory(raw)).toEqual([]);
    },
  );

  it("drops malformed entries and unknown verdicts but keeps the rest", () => {
    const raw = JSON.stringify([
      entry("a"),
      { id: 1, text: "x", at: 1 },
      { id: "b", text: "x" },
      { id: "c", text: "x", at: "now" },
      null,
      { ...entry("d"), labels: ["bogus"] },
    ]);
    expect(parseHistory(raw)).toEqual([entry("a"), entry("d")]);
  });

  it("keeps no more than the limit", () => {
    const many = Array.from({ length: HISTORY_LIMIT + 5 }, (_, i) =>
      entry(String(i)),
    );
    expect(parseHistory(JSON.stringify(many))).toHaveLength(HISTORY_LIMIT);
  });
});

describe("list changes", () => {
  it("puts a new check first", () => {
    expect(addEntry([entry("a")], entry("b")).map((e) => e.id)).toEqual([
      "b",
      "a",
    ]);
  });

  it("moves a repeated check up instead of listing it twice", () => {
    const list = addEntry([entry("a"), entry("b")], entry("b", 9));
    expect(list.map((e) => e.id)).toEqual(["b", "a"]);
    expect(list[0].at).toBe(9);
  });

  it("drops the oldest past the limit", () => {
    const full = Array.from({ length: HISTORY_LIMIT }, (_, i) =>
      entry(String(i)),
    );
    const list = addEntry(full, entry("new"));
    expect(list).toHaveLength(HISTORY_LIMIT);
    expect(list[0].id).toBe("new");
    expect(list.at(-1)?.id).toBe(String(HISTORY_LIMIT - 2));
  });

  it("removes one check", () => {
    expect(removeEntry([entry("a"), entry("b")], "a")).toEqual([entry("b")]);
  });

  it("adds verdicts to the matching check only", () => {
    const list = withLabels([entry("a"), entry("b")], "b", ["cant_check"]);
    expect(list[0].labels).toBeUndefined();
    expect(list[1].labels).toEqual(["cant_check"]);
  });
});

describe("historyStore", () => {
  beforeEach(() => {
    localStorage.clear();
    historyStore.clear();
  });

  it("stores a check and tells subscribers", () => {
    const seen = vi.fn();
    const off = historyStore.subscribe(seen);
    historyStore.add("a", "some claim");
    expect(seen).toHaveBeenCalled();
    expect(historyStore.getSnapshot()).toMatchObject([
      { id: "a", text: "some claim" },
    ]);
    off();
  });

  it("returns the same array while nothing changed", () => {
    historyStore.add("a", "x");
    expect(historyStore.getSnapshot()).toBe(historyStore.getSnapshot());
  });

  it("records verdicts for a stored check, and ignores one it never stored", () => {
    historyStore.add("a", "x");
    historyStore.finish("a", ["supported"]);
    historyStore.finish("zzz", ["supported"]);
    const list = historyStore.getSnapshot();
    expect(list).toHaveLength(1);
    expect(list[0].labels).toEqual(["supported"]);
  });

  it("clears the storage key when emptied", () => {
    historyStore.add("a", "x");
    expect(localStorage.getItem(HISTORY_KEY)).not.toBeNull();
    historyStore.clear();
    expect(localStorage.getItem(HISTORY_KEY)).toBeNull();
    expect(historyStore.getSnapshot()).toEqual([]);
  });

  it("is empty on the server", () => {
    expect(historyStore.getServerSnapshot()).toEqual([]);
  });
});
