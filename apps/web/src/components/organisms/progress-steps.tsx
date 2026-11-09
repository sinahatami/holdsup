import { Eyebrow } from "@/components/atoms/eyebrow";
import { ProgressMark } from "@/components/atoms/progress-mark";
import type { Stage } from "@/lib/progress";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/**
 * Where a running check is: finding the series, fetching the data, recomputing, writing the
 * explanation, done. Each stage follows the live trace, so it moves when the server moves.
 */
export function ProgressSteps({ stages }: { stages: readonly Stage[] }) {
  const t = strings.progress;
  return (
    <section
      aria-labelledby="progress-heading"
      className="glass flex flex-col gap-4 rounded-3xl p-6"
    >
      <Eyebrow id="progress-heading">{t.heading}</Eyebrow>
      <ol className="grid gap-3 sm:grid-cols-5 sm:gap-2">
        {stages.map(({ id, state }) => (
          <li
            key={id}
            data-state={state}
            aria-current={state === "running" ? "step" : undefined}
            className="flex items-center gap-3 text-sm sm:flex-col sm:items-start sm:gap-2"
          >
            <ProgressMark state={state} />
            <span
              className={cn(
                "leading-5",
                state === "pending" || state === "skipped"
                  ? "text-muted-foreground"
                  : "font-medium",
              )}
            >
              {t.stages[id]}
              <span className="sr-only"> ({t.state[state]})</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
