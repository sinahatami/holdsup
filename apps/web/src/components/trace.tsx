import { Check, Loader2, TriangleAlert } from "lucide-react";
import type { TraceRow } from "@/lib/use-check";
import { strings } from "@/lib/strings";

export function Trace({ rows }: { rows: TraceRow[] }) {
  if (rows.length === 0) return null;
  return (
    <section
      aria-labelledby="trace-heading"
      className="glass flex flex-col gap-4 rounded-3xl p-6"
    >
      <h2
        id="trace-heading"
        className="text-muted-foreground text-xs font-semibold tracking-widest uppercase"
      >
        {strings.check.traceHeading}
      </h2>
      <ol aria-live="polite" className="flex flex-col text-sm">
        {rows.map((r, i) => (
          <li
            key={r.key}
            className="relative flex items-start gap-3 pb-4 last:pb-0"
            data-state={r.state}
          >
            {i < rows.length - 1 && (
              <span
                aria-hidden
                className="bg-border absolute start-3 top-7 bottom-1 w-px"
              />
            )}
            <span
              className={`relative flex size-6 shrink-0 items-center justify-center rounded-full ${
                r.state === "running"
                  ? "bg-accent text-brand"
                  : r.state === "ok"
                    ? "bg-primary text-primary-foreground"
                    : "text-[var(--v-framing)] bg-[var(--v-framing-bg)]"
              }`}
            >
              {r.state === "running" ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
              ) : r.state === "ok" ? (
                <Check className="size-3.5" aria-hidden />
              ) : (
                <TriangleAlert className="size-3.5" aria-hidden />
              )}
            </span>
            <span className="pt-0.5 leading-5">
              {r.claim !== null && (
                <span className="text-muted-foreground">#{r.claim + 1} </span>
              )}
              <span className="font-medium">{strings.steps[r.step]}</span>
              <span className="sr-only"> ({strings.stepState[r.state]})</span>
              {r.summary && (
                <span className="text-muted-foreground"> — {r.summary}</span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
