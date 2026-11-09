"use client";

import { pill } from "@/components/atoms/pill";
import { CatalogFilters } from "@/components/organisms/catalog-filters";
import { CatalogList } from "@/components/organisms/catalog-list";
import { useCatalogFilter } from "@/hooks/use-catalog-filter";
import type { CatalogEntry } from "@/lib/api/client";
import { filterCatalog, isFiltered } from "@/lib/catalog-filter";
import { strings } from "@/lib/strings";

type Theme = CatalogEntry["theme"];
const themes = Object.keys(strings.indicators.themes) as Theme[];

/** Every statistic HoldsUp can check, with the controls that narrow the list down. */
export function CatalogExplorer({ entries }: { entries: CatalogEntry[] }) {
  const t = strings.indicators;
  const { filter, version, change, clear } = useCatalogFilter();
  const matches = filterCatalog(entries, filter);
  const themeCounts = Object.fromEntries(themes.map((k) => [k, 0])) as Record<
    Theme,
    number
  >;
  for (const e of filterCatalog(entries, filter, "theme"))
    themeCounts[e.theme]++;

  const clearButton = (
    <button type="button" onClick={clear} className={pill({ tone: "glass" })}>
      {t.clear}
    </button>
  );

  return (
    <div className="flex flex-col gap-8">
      <CatalogFilters
        entries={entries}
        filter={filter}
        themeCounts={themeCounts}
        version={version}
        onChange={change}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="text-muted-foreground text-sm">
          {t.shown(matches.length, entries.length)}
        </p>
        {isFiltered(filter) && matches.length > 0 && clearButton}
      </div>
      {matches.length > 0 ? (
        <CatalogList entries={matches} />
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
