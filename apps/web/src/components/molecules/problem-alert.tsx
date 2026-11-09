import { OctagonAlert } from "lucide-react";
import type { ReactNode } from "react";
import { problemKind, problemMessage, type Problem } from "@/lib/api/client";
import { strings } from "@/lib/strings";

/**
 * A failed check: what went wrong, in words that fit the kind of failure, and when the API
 * says to wait, how long. `action` is what the reader can do about it, such as trying again.
 */
export function ProblemAlert({
  problem,
  action,
}: {
  problem: Problem;
  action?: ReactNode;
}) {
  return (
    <div
      role="alert"
      data-verdict="not_supported"
      className="glass flex gap-3 rounded-2xl p-5"
      style={{ borderColor: "color-mix(in oklch, var(--v) 40%, transparent)" }}
    >
      <OctagonAlert
        className="mt-0.5 size-5 shrink-0"
        style={{ color: "var(--v)" }}
        aria-hidden
      />
      <div className="flex flex-col gap-3">
        <div>
          <h2 className="font-semibold">
            {strings.problem.heading[problemKind(problem)]}
          </h2>
          <p className="text-muted-foreground">{problemMessage(problem)}</p>
          {problem.retry_after ? (
            <p className="text-muted-foreground">
              {strings.check.retryAfter(problem.retry_after)}
            </p>
          ) : null}
        </div>
        {action}
      </div>
    </div>
  );
}
