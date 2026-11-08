import { OctagonAlert } from "lucide-react";
import { problemMessage, type Problem } from "@/lib/api/client";
import { strings } from "@/lib/strings";

/** A failed check: what went wrong and, when rate limited, when to try again. */
export function ProblemAlert({ problem }: { problem: Problem }) {
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
      <div>
        <h2 className="font-semibold">{strings.check.errorHeading}</h2>
        <p className="text-muted-foreground">{problemMessage(problem)}</p>
        {problem.retry_after ? (
          <p className="text-muted-foreground">
            {strings.check.retryAfter(problem.retry_after)}
          </p>
        ) : null}
      </div>
    </div>
  );
}
