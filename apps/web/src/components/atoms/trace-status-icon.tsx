import { Check, Loader2, TriangleAlert, type LucideIcon } from "lucide-react";
import type { TraceState } from "@/lib/trace";
import { cn } from "@/lib/utils";

// One entry per state: adding a state is one line here, not another branch.
const LOOK: Record<
  TraceState,
  { Icon: LucideIcon; tone: string; spin?: true }
> = {
  running: { Icon: Loader2, tone: "bg-accent text-brand", spin: true },
  ok: { Icon: Check, tone: "bg-primary text-primary-foreground" },
  cant_check: {
    Icon: TriangleAlert,
    tone: "text-[var(--v-framing)] bg-[var(--v-framing-bg)]",
  },
};

/** The round marker beside a trace step. Decorative: the state is also in words. */
export function TraceStatusIcon({ state }: { state: TraceState }) {
  const { Icon, tone, spin } = LOOK[state];
  return (
    <span
      className={cn(
        "relative flex size-6 shrink-0 items-center justify-center rounded-full",
        tone,
      )}
    >
      <Icon className={cn("size-3.5", spin && "animate-spin")} aria-hidden />
    </span>
  );
}
