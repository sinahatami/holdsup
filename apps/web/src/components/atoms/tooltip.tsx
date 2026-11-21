"use client";

import { ArrowUpRight } from "lucide-react";
import { useState, type ReactNode } from "react";

/**
 * A short label shown beside a control that is only an icon, for sighted readers: after a
 * moment of hovering with a mouse, or at once when the control has keyboard focus. Escape
 * hides it until the pointer or focus leaves (WCAG 1.4.13), and it stays while hovered, so
 * it can be read under a magnifier. The control must carry the same words as its own name
 * (`aria-label` or hidden text): the tooltip is hidden from assistive technology, so it is
 * never read twice. Touch screens have no hover, which is why it is only ever a repeat.
 *
 * The look lives in globals.css (`.tip`): an ink label with a caret pointing at the
 * control, which settles in towards it. `external` adds the arrow every link off the site
 * carries, so the reader knows before clicking that it leaves HoldsUp.
 */
export function Tooltip({
  label,
  side = "bottom",
  align = "center",
  external = false,
  children,
}: {
  label: string;
  side?: "top" | "bottom";
  align?: "start" | "center" | "end";
  external?: boolean;
  children: ReactNode;
}) {
  const [dismissed, setDismissed] = useState(false);
  return (
    <span
      className="tip-anchor"
      data-dismissed={dismissed || undefined}
      onKeyDown={(e) => {
        if (e.key === "Escape") setDismissed(true);
      }}
      onPointerLeave={() => setDismissed(false)}
      onBlur={() => setDismissed(false)}
    >
      {children}
      <span
        aria-hidden
        data-testid="tooltip"
        data-side={side}
        data-align={align}
        className="tip"
      >
        <span className="tip-label">
          {label}
          {external && <ArrowUpRight className="size-3 opacity-70" />}
        </span>
      </span>
    </span>
  );
}
