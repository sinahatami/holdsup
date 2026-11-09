import type { Label } from "@/lib/api/client";

/**
 * The checks a person made in this browser, kept in localStorage as an external
 * store (like the theme). No account and nothing leaves the browser: the server
 * has the checks themselves, this only remembers which ones were yours.
 */

export interface HistoryEntry {
  id: string;
  /** The text that was sent. */
  text: string;
  /** Epoch milliseconds when it was sent. */
  at: number;
  /** One verdict per claim, once the check has finished. */
  labels?: Label[];
}

export const HISTORY_KEY = "holdsup-history";

/** The oldest entries fall off past this, so the list (and storage) stay small. */
export const HISTORY_LIMIT = 30;

const LABELS: ReadonlySet<string> = new Set([
  "supported",
  "supported_framing_matters",
  "partly_supported",
  "not_supported",
  "cant_check",
]);

const isLabel = (v: unknown): v is Label =>
  typeof v === "string" && LABELS.has(v);

/** Reads what was stored; anything malformed is dropped, never thrown. */
export function parseHistory(raw: string | null): HistoryEntry[] {
  if (!raw) return [];
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(data)) return [];
  const entries: HistoryEntry[] = [];
  for (const item of data) {
    if (typeof item !== "object" || item === null) continue;
    const { id, text, at, labels } = item as Record<string, unknown>;
    if (typeof id !== "string" || typeof text !== "string") continue;
    if (typeof at !== "number" || !Number.isFinite(at)) continue;
    const entry: HistoryEntry = { id, text, at };
    if (Array.isArray(labels) && labels.every(isLabel)) entry.labels = labels;
    entries.push(entry);
  }
  return entries.slice(0, HISTORY_LIMIT);
}

/** Puts a check first; sending the same check again moves it up instead of repeating it. */
export function addEntry(
  list: readonly HistoryEntry[],
  entry: HistoryEntry,
): HistoryEntry[] {
  return [entry, ...list.filter((e) => e.id !== entry.id)].slice(
    0,
    HISTORY_LIMIT,
  );
}

export function removeEntry(
  list: readonly HistoryEntry[],
  id: string,
): HistoryEntry[] {
  return list.filter((e) => e.id !== id);
}

/** Records a check's verdicts; a check that is not in the list stays out of it. */
export function withLabels(
  list: readonly HistoryEntry[],
  id: string,
  labels: Label[],
): HistoryEntry[] {
  return list.map((e) => (e.id === id ? { ...e, labels } : e));
}

const EMPTY: HistoryEntry[] = [];
const listeners = new Set<() => void>();

// useSyncExternalStore needs the same array back while nothing changed.
let cachedRaw: string | null | undefined;
let cached: HistoryEntry[] = EMPTY;

function readRaw(): string | null {
  try {
    return localStorage.getItem(HISTORY_KEY);
  } catch {
    return null;
  }
}

function getSnapshot(): HistoryEntry[] {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = parseHistory(raw);
  }
  return cached;
}

function write(list: HistoryEntry[]): void {
  try {
    if (list.length === 0) localStorage.removeItem(HISTORY_KEY);
    else localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
  } catch {}
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  // Another tab changed it.
  const onStorage = (e: StorageEvent) => {
    if (e.key === HISTORY_KEY || e.key === null) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export const historyStore = {
  subscribe,
  getSnapshot,
  getServerSnapshot: (): HistoryEntry[] => EMPTY,
  add: (id: string, text: string) =>
    write(addEntry(getSnapshot(), { id, text, at: Date.now() })),
  finish: (id: string, labels: Label[]) => {
    const list = getSnapshot();
    if (list.some((e) => e.id === id)) write(withLabels(list, id, labels));
  },
  remove: (id: string) => write(removeEntry(getSnapshot(), id)),
  clear: () => write([]),
};
