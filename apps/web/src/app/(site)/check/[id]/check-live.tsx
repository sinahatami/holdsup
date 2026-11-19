"use client";

import type { ReactNode } from "react";
import { BackLink } from "@/components/molecules/back-link";
import { CheckReport } from "@/components/organisms/check-report";
import { CheckTemplate } from "@/components/templates/check-template";
import { useCheck } from "@/hooks/use-check";

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
  return (
    <CheckTemplate actions={<BackLink />}>
      <CheckReport
        state={state}
        onReconnect={reconnect}
        whileYouWait={whileYouWait}
      />
    </CheckTemplate>
  );
}
