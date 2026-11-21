import { WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { Arrival } from "@/components/atoms/arrival";
import { CheckPlaceholder } from "@/components/molecules/check-placeholder";
import { Notice } from "@/components/molecules/notice";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { RetryButton } from "@/components/molecules/retry-button";
import { CheckResultView } from "@/components/organisms/check-result";
import { ProgressSteps } from "@/components/organisms/progress-steps";
import { Trace } from "@/components/organisms/trace";
import type { CheckState } from "@/hooks/use-check";
import { isRetryable, problemKind } from "@/lib/api/client";
import { progressOf } from "@/lib/progress";
import { strings } from "@/lib/strings";

/**
 * Everything known about a check so far: status, problems, the trace, the result.
 * `onReconnect` follows the check again after its live connection was lost.
 * `whileYouWait` is shown under the problem when HoldsUp is at capacity (the page fills it
 * with checks done earlier).
 */
export function CheckReport({
  state,
  onReconnect,
  whileYouWait,
}: {
  state: CheckState;
  onReconnect?: () => void;
  whileYouWait?: ReactNode;
}) {
  const { loading, text, trace, result, error, connectionLost } = state;
  // A check being followed live shows its progress; one that was read whole has no trace to show.
  const following = !loading && (trace.length > 0 || (!result && !error));
  return (
    <>
      {loading && <CheckPlaceholder />}
      {error && (
        <ProblemAlert
          problem={error}
          action={
            text && isRetryable(error) ? (
              <RetryButton text={text} retryAfter={error.retry_after} />
            ) : undefined
          }
        />
      )}
      {error && problemKind(error) === "at_capacity" && whileYouWait}
      {connectionLost && !result && (
        <Notice icon={WifiOff}>
          {strings.check.connectionLost}
          {onReconnect && (
            <button
              type="button"
              onClick={onReconnect}
              className="text-brand ms-1 font-medium underline underline-offset-4"
            >
              {strings.problem.reconnect}
            </button>
          )}
        </Notice>
      )}
      {following && (
        <ProgressSteps
          stages={progressOf(trace, {
            finished: result !== null,
            stopped: error !== null || connectionLost,
          })}
        />
      )}
      <Trace rows={trace} />
      {result && (
        // A result that ends a check the reader followed is brought to them; one read whole
        // (no trace) is simply the page.
        <Arrival announce={trace.length > 0} label={strings.check.resultLabel}>
          <CheckResultView result={result} />
        </Arrival>
      )}
    </>
  );
}
