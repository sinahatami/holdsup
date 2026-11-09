"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import { TitledSection } from "@/components/molecules/titled-section";
import { useHistory } from "@/hooks/use-history";
import { formatLocalMoment } from "@/lib/format";
import { countHolding } from "@/lib/gallery";
import { historyStore } from "@/lib/history";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.history;

/**
 * The checks this browser sent, newest first, each a link to its receipt. It shows
 * nothing until there is something to show (and nothing on the server), so a first
 * visit looks exactly as it did before.
 */
export function HistoryList() {
  const entries = useHistory();
  if (entries.length === 0) return null;

  return (
    <TitledSection id="history" title={t.heading}>
      <p className="text-muted-foreground -mt-2 text-sm">{t.note}</p>
      <ul className="flex flex-col gap-3">
        {entries.map((e) => {
          const { holds, total } = countHolding(
            (e.labels ?? []).map((label) => ({ label })),
          );
          return (
            <li
              key={e.id}
              className="glass group hover:border-brand/50 relative flex items-start gap-3 rounded-2xl p-4 transition"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-2">
                <Link
                  href={routes.check(e.id)}
                  className="line-clamp-2 leading-7 font-medium after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
                >
                  {e.text}
                </Link>
                <div className="text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  <time dateTime={new Date(e.at).toISOString()}>
                    {formatLocalMoment(e.at)}
                  </time>
                  {!e.labels?.length ? (
                    <span>{t.running}</span>
                  ) : (
                    total > 1 && <span>{t.summary(holds, total)}</span>
                  )}
                </div>
                {e.labels && e.labels.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {[...new Set(e.labels)].map((label) => (
                      <VerdictBadge key={label} label={label} />
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => historyStore.remove(e.id)}
                aria-label={t.remove(e.text)}
                title={t.remove(e.text)}
                className="text-muted-foreground hover:text-foreground focus-visible:ring-ring/50 relative z-10 flex size-9 shrink-0 items-center justify-center rounded-full focus-visible:ring-4 focus-visible:outline-none"
              >
                <X className="size-4" aria-hidden />
              </button>
            </li>
          );
        })}
      </ul>
      <p>
        <button
          type="button"
          onClick={historyStore.clear}
          className="text-brand font-medium underline underline-offset-4"
        >
          {t.clear}
        </button>
      </p>
    </TitledSection>
  );
}
