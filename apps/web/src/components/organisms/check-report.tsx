import { WifiOff } from "lucide-react";
import { StatusText } from "@/components/atoms/status-text";
import { Notice } from "@/components/molecules/notice";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { RetryButton } from "@/components/molecules/retry-button";
import { CheckResultView } from "@/components/organisms/check-result";
import { ProgressSteps } from "@/components/organisms/progress-steps";
import { Trace } from "@/components/organisms/trace";
import type { CheckState } from "@/hooks/use-check";
import { isRetryable } from "@/lib/api/client";
import { progressOf } from "@/lib/progress";
import { strings } from "@/lib/strings";

/**
 * Everything known about a check so far: status, problems, the trace, the result.
 * `onReconnect` follows the check again after its live connection was lost.
 */
export function CheckReport({
  state,
  onReconnect,
}: {
  state: CheckState;
  onReconnect?: () => void;
}) {
  const { loading, text, trace, result, error, connectionLost } = state;
  // A check being followed live shows its progress; one that was read whole has no trace to show.
  const following = !loading && (trace.length > 0 || (!result && !error));
  return (
    <>
      {loading && <StatusText>{strings.check.loading}</StatusText>}
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
      {result && <CheckResultView result={result} />}
    </>
  );
}
