"use client";

import { useSyncExternalStore } from "react";
import { themeStore, type Theme } from "@/lib/theme";

/** The current theme and a setter; every subscriber re-renders on change. */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const theme = useSyncExternalStore(
    themeStore.subscribe,
    themeStore.getSnapshot,
    themeStore.getServerSnapshot,
  );
  return [theme, themeStore.set];
}
