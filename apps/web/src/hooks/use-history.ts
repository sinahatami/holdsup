"use client";

import { useSyncExternalStore } from "react";
import { historyStore, type HistoryEntry } from "@/lib/history";

/** The checks made in this browser, newest first; empty on the server and before hydration. */
export function useHistory(): HistoryEntry[] {
  return useSyncExternalStore(
    historyStore.subscribe,
    historyStore.getSnapshot,
    historyStore.getServerSnapshot,
  );
}
