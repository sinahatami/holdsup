"use client";

import { ArrowUp } from "lucide-react";
import { Tooltip } from "@/components/atoms/tooltip";
import { useScrolledPast } from "@/hooks/use-scrolled-past";
import { strings } from "@/lib/strings";

function toTop() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  // The button leaves once the page is back at the top, so keyboard focus goes to the first
  // link in the header (the logo) instead of falling back to the body.
  document
    .querySelector<HTMLElement>("header a")
    ?.focus({ preventScroll: true });
}

/** A round button in the bottom-end corner, shown once the reader is a screen down. */
export function BackToTop() {
  const shown = useScrolledPast(1);
  if (!shown) return null;
  return (
    // The tooltip goes above, and lines up with the corner, so it stays on screen.
    <div className="rise fixed end-4 bottom-4 z-30 sm:end-6 sm:bottom-6 print:hidden">
      <Tooltip label={strings.nav.backToTop} side="top" align="end">
        <button
          type="button"
          onClick={toTop}
          aria-label={strings.nav.backToTop}
          className="glass text-muted-foreground hover:text-foreground focus-visible:ring-ring flex size-11 items-center justify-center rounded-full transition focus-visible:ring-2 focus-visible:outline-none"
        >
          <ArrowUp className="size-5" aria-hidden />
        </button>
      </Tooltip>
    </div>
  );
}
