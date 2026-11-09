import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/** The share of the limit at which the counter starts to warn. */
const WARN_AT = 0.9;

/**
 * "120 / 2,000". Near the limit it turns amber and says how many are left; over
 * it, red. Bold as well as coloured, so colour is not the only signal. Hidden
 * from screen readers: the alert says it.
 */
export function CharCounter({ count, max }: { count: number; max: number }) {
  const over = count > max;
  const near = !over && count >= max * WARN_AT;
  return (
    <span
      aria-hidden
      className={cn(
        "px-1 text-xs whitespace-nowrap tabular-nums",
        over && "text-destructive font-semibold",
        near && "font-semibold text-(--v-framing)",
        !over && !near && "text-muted-foreground",
      )}
    >
      {count.toLocaleString()} / {max.toLocaleString()}
      {near && ` · ${strings.home.charsLeft((max - count).toLocaleString())}`}
    </span>
  );
}
