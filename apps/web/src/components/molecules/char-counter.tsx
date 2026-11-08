import { cn } from "@/lib/utils";

/** "120 / 2,000", red once over the limit. Hidden from screen readers: the alert says it. */
export function CharCounter({ count, max }: { count: number; max: number }) {
  return (
    <span
      aria-hidden
      className={cn(
        "px-1 text-xs tabular-nums",
        count > max ? "text-destructive" : "text-muted-foreground",
      )}
    >
      {count.toLocaleString()} / {max.toLocaleString()}
    </span>
  );
}
