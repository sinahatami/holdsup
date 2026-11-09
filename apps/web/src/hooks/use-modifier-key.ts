"use client";

import { useSyncExternalStore } from "react";

const noop = () => () => {};

function isApple(): boolean {
  return /Mac|iPhone|iPad|iPod/.test(navigator.userAgent);
}

/**
 * The name of the key that, with Enter, submits a form on this device: "⌘" on
 * Apple devices, "Ctrl" elsewhere. Renders "Ctrl" on the server and before
 * hydration, then switches, so the markup always matches.
 */
export function useModifierKey(): "⌘" | "Ctrl" {
  return useSyncExternalStore(
    noop,
    () => (isApple() ? "⌘" : "Ctrl"),
    () => "Ctrl",
  );
}
