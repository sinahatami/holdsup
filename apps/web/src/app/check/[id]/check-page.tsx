import { notFound } from "next/navigation";
import { Suspense } from "react";
import { BackLink } from "@/components/molecules/back-link";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { RetryButton } from "@/components/molecules/retry-button";
import { CheckResultView } from "@/components/organisms/check-result";
import { CheckTemplate } from "@/components/templates/check-template";
import { readCheck } from "@/lib/api/check";
import { isRetryable, problemKind } from "@/lib/api/client";
import { CheckLive } from "./check-live";
import { WhileYouWait } from "./while-you-wait";

/**
 * A check at its permanent link. One that has finished is drawn here, on the
 * server, from what the API stored: nothing is re-run, and the receipt is in
 * the page itself. One still running, or that the server could not read, goes
 * to the browser, which follows its live trace. A check that found HoldsUp at
 * capacity, stored or live, shows checks done earlier below the problem.
 */
export async function CheckPage({ id }: { id: string }) {
  const found = await readCheck(id);
  if (found.kind === "missing") notFound();
  if (found.kind === "unavailable") return <CheckLive id={id} />;

  const { result, error, status, text } = found.view;
  if (result) {
    return (
      <CheckTemplate actions={<BackLink />}>
        <CheckResultView result={result} />
      </CheckTemplate>
    );
  }
  // The gallery read is cached and streams in on its own, so it never holds up the check.
  const whileYouWait = (
    <Suspense fallback={null}>
      <WhileYouWait />
    </Suspense>
  );
  if (status === "failed" && error) {
    return (
      <CheckTemplate actions={<BackLink />}>
        <ProblemAlert
          problem={error}
          action={
            isRetryable(error) ? (
              <RetryButton text={text} retryAfter={error.retry_after} />
            ) : undefined
          }
        />
        {problemKind(error) === "at_capacity" && whileYouWait}
      </CheckTemplate>
    );
  }
  return <CheckLive id={id} whileYouWait={whileYouWait} />;
}
