import {
  Check,
  Loader2,
  Minus,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { StageState } from "@/lib/progress";
import { cn } from "@/lib/utils";

const LOOK: Record<
  StageState,
  { Icon: LucideIcon | null; tone: string; spin?: true }
> = {
  pending: { Icon: null, tone: "border-2 border-border" },
  running: { Icon: Loader2, tone: "bg-accent text-brand", spin: true },
  done: { Icon: Check, tone: "bg-primary text-primary-foreground" },
  stopped: {
    Icon: TriangleAlert,
    tone: "text-[var(--v-framing)] bg-[var(--v-framing-bg)]",
  },
  skipped: { Icon: Minus, tone: "bg-muted text-muted-foreground" },
};

/** The round marker of one stage of a check. Decorative: the state is also in words. */
export function ProgressMark({ state }: { state: StageState }) {
  const { Icon, tone, spin } = LOOK[state];
  return (
    <span
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-full",
        tone,
      )}
    >
      {Icon && (
        <Icon
          className={cn("size-3.5", spin && "motion-safe:animate-spin")}
          aria-hidden
        />
      )}
    </span>
  );
}
