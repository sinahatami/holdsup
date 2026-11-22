// A client component for its size, not for state: its path is 3.4 kB, and a server component
// writes it into a page's RSC payload once for every logo drawn there (the header, the footer
// and the not-found frames sent with each page), which was 12 copies on a check page. As a
// client component the path ships once, in a cached script, and the payload holds only props.
"use client";

import { LOGO_DOT, LOGO_INK, LOGO_VIEWBOX } from "@/lib/logo-art";
import { cn } from "@/lib/utils";

/**
 * The HoldsUp logo: a division sign whose upper dot is a quotation mark (a claim over its
 * denominator), then the name. The ink takes the text colour and the denominator is the
 * record blue, so it follows the theme. Give it a height; the width follows.
 * With a `label` it is an image of that name; without one it is decoration, for a parent
 * that already says "HoldsUp" (such as the home link).
 */
export function LogoLockup({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <svg
      viewBox={LOGO_VIEWBOX}
      className={cn("block h-7 w-auto shrink-0", className)}
      focusable="false"
      {...(label
        ? { role: "img", "aria-label": label }
        : { "aria-hidden": true })}
    >
      <path d={LOGO_INK} fill="currentColor" />
      <circle
        cx={LOGO_DOT.cx}
        cy={LOGO_DOT.cy}
        r={LOGO_DOT.r}
        className="fill-brand"
      />
    </svg>
  );
}
