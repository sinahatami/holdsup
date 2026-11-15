import { barWidth } from "@/lib/benchmark";
import type { Rate } from "@/lib/api/client";

/**
 * A bar for a share, drawn beside the figure that says it in words (the figure is the
 * information; the bar only lets the eye compare). Hidden from assistive technology.
 */
export function RateBar({ rate }: { rate: Rate }) {
  return (
    <span
      aria-hidden
      className="bg-muted block h-2 w-full min-w-24 overflow-hidden rounded-full"
    >
      <span
        className="bg-brand block h-full rounded-full"
        style={{ inlineSize: barWidth(rate) }}
      />
    </span>
  );
}
