import type { GalleryItem, Label } from "@/lib/api/client";

type Theme = NonNullable<GalleryItem["claims"][number]["theme"]>;

/** What a visitor has asked the list of recent checks to narrow down to. */
export interface RecentFilter {
  /** Checks with a claim that got this verdict. */
  verdict: Label | null;
  /** Checks with a claim about this place (a code such as "IT" or "EU"). */
  place: string | null;
  /** Checks with a claim whose statistic is under this topic. */
  theme: Theme | null;
}

export const noRecentFilter: RecentFilter = {
  verdict: null,
  place: null,
  theme: null,
};

export function isRecentFiltered(f: RecentFilter): boolean {
  return f.verdict !== null || f.place !== null || f.theme !== null;
}

/**
 * Checks that match every part of the filter. A check can hold several claims, so it
 * matches a part when any of its claims does. `skip` leaves one part out, to count how
 * many results each choice of that part would give.
 */
export function filterRecent(
  items: readonly GalleryItem[],
  f: RecentFilter,
  skip?: "verdict" | "theme",
): GalleryItem[] {
  return items.filter((item) => {
    const claims = item.claims ?? [];
    if (
      skip !== "verdict" &&
      f.verdict !== null &&
      !claims.some((c) => c.label === f.verdict)
    )
      return false;
    if (
      skip !== "theme" &&
      f.theme !== null &&
      !claims.some((c) => c.theme === f.theme)
    )
      return false;
    if (f.place !== null && !claims.some((c) => c.geo === f.place))
      return false;
    return true;
  });
}

/** Every place the checks are about, as codes. */
export function recentPlaces(items: readonly GalleryItem[]): string[] {
  const places = new Set<string>();
  for (const item of items)
    for (const c of item.claims ?? []) if (c.geo) places.add(c.geo);
  return [...places];
}

/** The filter written in an address (`?verdict=supported&place=IT&theme=work`). */
export function readRecentFilter(
  params: { get(name: string): string | null },
  verdicts: readonly string[],
  themes: readonly string[],
): RecentFilter {
  const verdict = params.get("verdict");
  const theme = params.get("theme");
  const place = params.get("place");
  return {
    verdict:
      verdict !== null && verdicts.includes(verdict)
        ? (verdict as Label)
        : null,
    theme: theme !== null && themes.includes(theme) ? (theme as Theme) : null,
    place: place !== null && /^[A-Z]{2,5}$/.test(place) ? place : null,
  };
}

/** The query string for a filter, without the "?"; empty when nothing is asked. */
export function recentQuery(f: RecentFilter): string {
  const out = new URLSearchParams();
  if (f.verdict) out.set("verdict", f.verdict);
  if (f.place) out.set("place", f.place);
  if (f.theme) out.set("theme", f.theme);
  return out.toString();
}
