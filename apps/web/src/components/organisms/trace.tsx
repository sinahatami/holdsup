import { Eyebrow } from "@/components/atoms/eyebrow";
import { TraceStep } from "@/components/molecules/trace-step";
import type { TraceRow } from "@/lib/trace";
import { strings } from "@/lib/strings";

export function Trace({ rows }: { rows: TraceRow[] }) {
  if (rows.length === 0) return null;
  return (
    <section
      aria-labelledby="trace-heading"
      className="glass flex flex-col gap-4 rounded-3xl p-6"
    >
      <Eyebrow id="trace-heading">{strings.check.traceHeading}</Eyebrow>
      <ol aria-live="polite" className="flex flex-col text-sm">
        {rows.map((row, i) => (
          <TraceStep key={row.key} row={row} last={i === rows.length - 1} />
        ))}
      </ol>
    </section>
  );
}
