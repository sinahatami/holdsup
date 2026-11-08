import { TraceStatusIcon } from "@/components/atoms/trace-status-icon";
import type { TraceRow } from "@/lib/trace";
import { strings } from "@/lib/strings";

/** One step of the live trace; `last` drops the line joining it to the next step. */
export function TraceStep({ row, last }: { row: TraceRow; last: boolean }) {
  return (
    <li
      className="relative flex items-start gap-3 pb-4 last:pb-0"
      data-state={row.state}
    >
      {!last && (
        <span
          aria-hidden
          className="bg-border absolute start-3 top-7 bottom-1 w-px"
        />
      )}
      <TraceStatusIcon state={row.state} />
      <span className="pt-0.5 leading-5">
        {row.claim !== null && (
          <span className="text-muted-foreground">#{row.claim + 1} </span>
        )}
        <span className="font-medium">{strings.steps[row.step]}</span>
        <span className="sr-only"> ({strings.stepState[row.state]})</span>
        {row.summary && (
          <span className="text-muted-foreground"> — {row.summary}</span>
        )}
      </span>
    </li>
  );
}
