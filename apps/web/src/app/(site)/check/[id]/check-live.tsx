"use client";

import type { ReactNode } from "react";
import { BackLink } from "@/components/molecules/back-link";
import { CheckReport } from "@/components/organisms/check-report";
import { CheckTemplate } from "@/components/templates/check-template";
import { useCheck } from "@/hooks/use-check";
import { receiptFacts } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";

/**
 * Binds the live check (data) to the check template (presentation). `whileYouWait` is
 * drawn on the server and shown only if the check finds HoldsUp at capacity.
 */
export function CheckLive({
  id,
  whileYouWait,
}: {
  id: string;
  whileYouWait?: ReactNode;
}) {
  const { state, reconnect } = useCheck(id);
  const { result, error } = state;
  // "Checking" while it runs, "Receipt" once it has a result, plain "Check" if it failed.
  const heading = result
    ? strings.check.receiptHeading
    : error
      ? strings.check.heading
      : strings.check.runningHeading;
  return (
    <CheckTemplate
      heading={heading}
      facts={result ? receiptFacts(result) : undefined}
      actions={<BackLink />}
    >
      <CheckReport
        state={state}
        onReconnect={reconnect}
        whileYouWait={whileYouWait}
      />
    </CheckTemplate>
  );
}
