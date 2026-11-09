"use client";

import { BackLink } from "@/components/molecules/back-link";
import { CheckReport } from "@/components/organisms/check-report";
import { CheckTemplate } from "@/components/templates/check-template";
import { useCheck } from "@/hooks/use-check";

/** Binds the live check (data) to the check template (presentation). */
export function CheckLive({ id }: { id: string }) {
  const { state, reconnect } = useCheck(id);
  return (
    <CheckTemplate actions={<BackLink />}>
      <CheckReport state={state} onReconnect={reconnect} />
    </CheckTemplate>
  );
}
