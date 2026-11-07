import { Check, Loader2, TriangleAlert } from "lucide-react";
import type { TraceRow } from "@/lib/use-check";
import { strings } from "@/lib/strings";

export function Trace({ rows }: { rows: TraceRow[] }) {
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby="trace-heading" className="flex flex-col gap-2">
      <h2 id="trace-heading" className="text-lg font-semibold">
        {strings.check.traceHeading}
      </h2>
      <ol aria-live="polite" className="flex flex-col gap-1 text-sm">
        {rows.map((r) => (
          <li
            key={r.key}
            className="flex items-start gap-2"
            data-state={r.state}
          >
            {r.state === "running" ? (
              <Loader2 className="mt-0.5 size-4 animate-spin" aria-hidden />
            ) : r.state === "ok" ? (
              <Check className="mt-0.5 size-4" aria-hidden />
            ) : (
              <TriangleAlert className="mt-0.5 size-4" aria-hidden />
            )}
            <span>
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
