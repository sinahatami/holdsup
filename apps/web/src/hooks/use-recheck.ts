"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  browserApi,
  problemText,
  toProblem,
  type ApiClient,
} from "@/lib/api/client";
import { historyStore } from "@/lib/history";
import { routes } from "@/lib/routes";

/**
 * Checks one claim again with another statistic and opens the new check's page; keeps
 * which statistic is being sent and any error.
 */
export function useRecheck(
  checkId: string,
  claimIndex: number,
  quote: string,
  api: ApiClient = browserApi,
) {
  const router = useRouter();
  const [sending, setSending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function recheck(indicatorId: string) {
    if (sending) return;
    setSending(indicatorId);
    setError(null);
    try {
      const accepted = await api.recheckClaim(checkId, claimIndex, indicatorId);
      historyStore.add(accepted.id, quote);
      router.push(routes.check(accepted.id));
    } catch (err) {
      setSending(null);
      setError(problemText(toProblem(err)));
    }
  }

  return { recheck, sending, error };
}
