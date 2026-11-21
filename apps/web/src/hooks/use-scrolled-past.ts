"use client";

import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  window.addEventListener("scroll", onChange, { passive: true });
  window.addEventListener("resize", onChange);
  return () => {
    window.removeEventListener("scroll", onChange);
    window.removeEventListener("resize", onChange);
  };
}

/**
 * Whether the page is scrolled further down than `screens` viewport heights. False on the
 * server and before hydration, so nothing that depends on it is in the first paint.
 */
export function useScrolledPast(screens = 1): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.scrollY > window.innerHeight * screens,
    () => false,
  );
}
