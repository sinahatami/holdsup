import type { ReactNode } from "react";
import { pill } from "@/components/atoms/pill";
import { cn } from "@/lib/utils";

/**
 * A pill that turns one filter choice on or off. `pressed` says it is on (to a screen
 * reader too), and `count` how many results the choice would give.
 */
export function FilterButton({
  pressed,
  count,
  disabled,
  onClick,
  children,
}: {
  pressed: boolean;
  count: number;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        pill({ tone: "glass" }),
        "aria-pressed:bg-primary aria-pressed:text-primary-foreground aria-pressed:hover:bg-primary focus-visible:ring-ring/50 outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent",
      )}
    >
      {children}
      <span className="opacity-80">{count}</span>
    </button>
  );
}
