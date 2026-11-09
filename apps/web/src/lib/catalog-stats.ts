import type { CatalogEntry } from "@/lib/api/client";

export interface Coverage {
  statistics: number;
  topics: number;
  /** Source ids with how many statistics each supplies, largest first. */
  sources: { id: string; count: number }[];
  firstYear: number;
  /** null while any statistic is still being updated. */
  lastYear: number | null;
}

/** What the catalog covers, counted from the catalog itself; null for an empty one. */
export function coverage(entries: readonly CatalogEntry[]): Coverage | null {
  if (entries.length === 0) return null;
  const perSource = new Map<string, number>();
  for (const e of entries) {
    perSource.set(e.source, (perSource.get(e.source) ?? 0) + 1);
  }
  const ongoing = entries.some((e) => e.last_year === null);
  return {
    statistics: entries.length,
    topics: new Set(entries.map((e) => e.theme)).size,
    sources: [...perSource]
      .map(([id, count]) => ({ id, count }))
      .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id)),
    firstYear: Math.min(...entries.map((e) => e.first_year)),
    lastYear: ongoing
      ? null
      : Math.max(...entries.map((e) => e.last_year ?? 0)),
  };
}
