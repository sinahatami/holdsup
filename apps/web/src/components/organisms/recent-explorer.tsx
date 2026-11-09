"use client";

import { useState } from "react";
import { pill } from "@/components/atoms/pill";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { RecentFilters } from "@/components/organisms/recent-filters";
import { useRecentFilter } from "@/hooks/use-recent-filter";
import type { GalleryItem, Label } from "@/lib/api/client";
import {
  filterRecent,
  isRecentFiltered,
  recentPlaces,
  type RecentFilter,
} from "@/lib/recent-filter";
import { strings } from "@/lib/strings";

type Theme = NonNullable<GalleryItem["claims"][number]["theme"]>;
const t = strings.recent;
const verdicts = Object.keys(strings.verdicts) as Label[];
const themes = Object.keys(strings.indicators.themes) as Theme[];

/** How many checks are shown at first, and added by each "Show more". */
export const PAGE_SIZE = 12;

/** How many of `items` carry each key: a verdict, or a topic, of any of their claims. */
function count<K extends string>(
  keys: readonly K[],
  items: readonly GalleryItem[],
  of: (claim: GalleryItem["claims"][number]) => string | null | undefined,
): Record<K, number> {
  const out = Object.fromEntries(keys.map((k) => [k, 0])) as Record<K, number>;
  for (const item of items) {
    const seen = new Set(
      (item.claims ?? []).map(of).filter((k): k is K => k != null && k in out),
    );
    for (const k of seen) out[k]++;
  }
  return out;
}

/** The featured checks, with the controls that narrow them down and a button for more. */
export function RecentExplorer({ items }: { items: GalleryItem[] }) {
  const { filter, change, clear } = useRecentFilter();
  const [shown, setShown] = useState(PAGE_SIZE);
  const matches = filterRecent(items, filter);
  const visible = matches.slice(0, shown);

  // A new filter starts the list again from the top.
  const onChange = (patch: Partial<RecentFilter>) => {
    change(patch);
    setShown(PAGE_SIZE);
  };
  const onClear = () => {
    clear();
    setShown(PAGE_SIZE);
  };

  const byVerdict = filterRecent(items, filter, "verdict");
  const byTheme = filterRecent(items, filter, "theme");
  const clearButton = (
    <button type="button" onClick={onClear} className={pill({ tone: "glass" })}>
      {t.clear}
    </button>
  );

  return (
    <div className="flex flex-col gap-8">
      <RecentFilters
        filter={filter}
        places={recentPlaces(items)}
        verdictCounts={count(verdicts, byVerdict, (c) => c.label)}
        themeCounts={count(themes, byTheme, (c) => c.theme)}
        total={{ verdict: byVerdict.length, theme: byTheme.length }}
        onChange={onChange}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="text-muted-foreground text-sm">
          {t.shown(visible.length, matches.length, items.length)}
        </p>
        {isRecentFiltered(filter) && matches.length > 0 && clearButton}
      </div>
      {matches.length > 0 ? (
        <>
          <ul className="grid gap-4 sm:grid-cols-2">
            {visible.map((item) => (
              <GalleryCard key={item.id} item={item} />
            ))}
          </ul>
          {visible.length < matches.length && (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={() => setShown(shown + PAGE_SIZE)}
                className={pill({ tone: "glass" })}
              >
                {t.showMore}
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="glass flex flex-col items-start gap-4 rounded-2xl p-6">
          <p className="text-lg font-semibold">{t.none}</p>
          <p className="text-muted-foreground leading-7">{t.noneHint}</p>
          {clearButton}
        </div>
      )}
    </div>
  );
}
