import { barWidth } from "@/lib/benchmark";
import type { Rate } from "@/lib/api/client";

/**
 * A bar for a share, drawn beside the figure that says it in words (the figure is the
 * information; the bar only lets the eye compare). Hidden from assistive technology.
 * Blue is HoldsUp's own figure; ink is anything it is compared with.
 */
export function RateBar({
  rate,
  tone = "brand",
}: {
  rate: Rate;
  tone?: "brand" | "ink";
}) {
  return (
    <span
      aria-hidden
      className="bg-muted block h-2 w-full min-w-24 overflow-hidden"
    >
      <span
        className={`${tone === "brand" ? "bg-brand" : "bg-foreground/70"} block h-full`}
        style={{ inlineSize: barWidth(rate) }}
      />
    </span>
  );
}
