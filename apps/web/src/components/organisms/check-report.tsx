import { WifiOff } from "lucide-react";
import { StatusText } from "@/components/atoms/status-text";
import { Notice } from "@/components/molecules/notice";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { CheckResultView } from "@/components/organisms/check-result";
import { ProgressSteps } from "@/components/organisms/progress-steps";
import { Trace } from "@/components/organisms/trace";
import type { CheckState } from "@/hooks/use-check";
import { progressOf } from "@/lib/progress";
import { strings } from "@/lib/strings";

/** Everything known about a check so far: status, problems, the trace, the result. */
export function CheckReport({ state }: { state: CheckState }) {
  const { loading, trace, result, error, connectionLost } = state;
  // A check being followed live shows its progress; one that was read whole has no trace to show.
  const following = !loading && (trace.length > 0 || (!result && !error));
  return (
    <>
      {loading && <StatusText>{strings.check.loading}</StatusText>}
      {error && <ProblemAlert problem={error} />}
      {connectionLost && (
        <Notice icon={WifiOff}>{strings.check.connectionLost}</Notice>
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
