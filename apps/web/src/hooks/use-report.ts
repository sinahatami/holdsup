"use client";

import { useState } from "react";
import {
  browserApi,
  problemMessage,
  toProblem,
  type ApiClient,
  type ReportKind,
} from "@/lib/api/client";

export type ReportPhase = "idle" | "sending" | "sent";

/** Sends a reader's report about one claim of a check; keeps the sending state and the error. */
export function useReport(
  checkId: string,
  claimIndex: number,
  api: ApiClient = browserApi,
) {
  const [phase, setPhase] = useState<ReportPhase>("idle");
  const [error, setError] = useState<string | null>(null);

  async function send(kind: ReportKind, note: string) {
    if (phase === "sending") return;
    setPhase("sending");
    setError(null);
    try {
      await api.reportCheck(checkId, {
        kind,
        claim_index: claimIndex,
        note: note.trim(),
      });
      setPhase("sent");
    } catch (err) {
      setPhase("idle");
      setError(problemMessage(toProblem(err)));
    }
  }

  return { phase, error, send };
}
