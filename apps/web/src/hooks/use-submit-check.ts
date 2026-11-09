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

/** Sends a text to be checked and opens its live page; keeps the busy and error state. */
export function useSubmitCheck(api: ApiClient = browserApi) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(text: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const accepted = await api.submitCheck(text);
      historyStore.add(accepted.id, text);
      router.push(routes.check(accepted.id));
    } catch (err) {
      setBusy(false);
      setError(problemText(toProblem(err)));
    }
  }

  return { submit, busy, error };
}
