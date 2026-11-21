"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Wraps something the reader was waiting for. It rises in; when `announce` is set (it arrived
 * while the reader watched, not with the page), it is also scrolled into view and takes
 * keyboard focus, so a screen reader reads it and the next Tab starts from it.
 */
export function Arrival({
  announce,
  label,
  children,
}: {
  announce: boolean;
  /** Names the region the focus lands on. */
  label: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!announce || !el) return;
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    el.focus({ preventScroll: true });
    el.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "start",
    });
    // Only when it first arrives: a later render must not pull the reader back.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div
      ref={ref}
      role="region"
      aria-label={label}
      tabIndex={-1}
      className="rise scroll-mt-24 outline-none"
    >
      {children}
    </div>
  );
}
