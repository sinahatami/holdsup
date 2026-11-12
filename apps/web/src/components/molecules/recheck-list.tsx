"use client";

import { RefreshCw } from "lucide-react";
import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { useRecheck } from "@/hooks/use-recheck";
import type { Suggestion } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.recheck;

/**
 * Statistics a claim can be checked with instead, each with a button that starts that
 * re-check and opens it. The result of a failed start is said in a status line.
 */
export function RecheckList({
  checkId,
  claimIndex,
  quote,
  statistics,
  linkFor,
}: {
  checkId: string;
  claimIndex: number;
  /** The claim's words, for the reader's history of checks. */
  quote: string;
  statistics: readonly Suggestion[];
  /** Where a statistic's name links (the catalog), if it links anywhere. */
  linkFor?: (s: Suggestion) => string;
}) {
  const { recheck, sending, error } = useRecheck(checkId, claimIndex, quote);
  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-2">
        {statistics.map((s) => (
          <li
            key={s.id}
            className="flex flex-wrap items-center gap-x-3 gap-y-1"
          >
            {linkFor ? (
              <Link
                href={linkFor(s)}
                className="text-brand leading-6 font-medium underline underline-offset-4"
              >
                {s.name}
              </Link>
            ) : (
              <span className="leading-6">{s.name}</span>
            )}
            <button
              type="button"
              aria-label={t.actionLabel(s.name)}
              disabled={sending !== null}
              onClick={() => recheck(s.id)}
              className={pill({ tone: "glass" })}
            >
              <RefreshCw className="size-4" aria-hidden />
              {sending === s.id ? t.sending : t.action}
            </button>
          </li>
        ))}
      </ul>
      <p role="status" className="text-destructive min-h-5 text-sm">
        {error}
      </p>
    </div>
  );
}
