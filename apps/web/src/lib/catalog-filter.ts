import type { CatalogEntry } from "@/lib/api/client";

/** What a visitor has asked the catalog page to narrow down to. Every field is optional. */
export interface CatalogFilter {
  /** Words to find; every word has to appear somewhere in the entry. */
  q: string;
  theme: CatalogEntry["theme"] | null;
  /** A place code: a country ("IT") or a group ("EU", "WORLD"). */
  place: string | null;
  /** The years a series has to reach into, both ends included. */
  from: number | null;
  to: number | null;
}

export const noFilter: CatalogFilter = {
  q: "",
  theme: null,
  place: null,
  from: null,
  to: null,
};

const KEYS = ["q", "theme", "place", "from", "to"] as const;

/** Lower case with accents dropped, so "inflacion" finds "Inflación" and case never matters. */
function plain(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

function haystack(e: CatalogEntry): string {
  return plain(
    [e.name, e.definition, e.unit, e.source, e.source_code, ...e.aliases].join(
      " ",
    ),
  );
}

/** True when the filter asks for something. */
export function isFiltered(f: CatalogFilter): boolean {
  return (
    f.q.trim() !== "" ||
    f.theme !== null ||
    f.place !== null ||
    f.from !== null ||
    f.to !== null
  );
}

/** True when the first year asked for comes after the last: nothing can match. */
export function yearsBackwards(f: CatalogFilter): boolean {
  return f.from !== null && f.to !== null && f.from > f.to;
}

/** A place is a group when the catalog lists it as one; any other code is a country. */
function isGroup(entries: readonly CatalogEntry[], place: string): boolean {
  return entries.some((e) => e.groups.includes(place));
}

function coversPlace(e: CatalogEntry, place: string, group: boolean): boolean {
  if (group) return e.groups.includes(place);
  // "Every country" covers a country the catalog never names too.
  return e.all_countries || e.countries.includes(place);
}

/** Entries that match every part of the filter; `skip` leaves one part out (for counting a facet). */
export function filterCatalog(
  entries: readonly CatalogEntry[],
  f: CatalogFilter,
  skip?: "theme",
): CatalogEntry[] {
  if (yearsBackwards(f)) return [];
  const words = plain(f.q).split(/\s+/).filter(Boolean);
  const group = f.place !== null && isGroup(entries, f.place);
  return entries.filter((e) => {
    if (skip !== "theme" && f.theme !== null && e.theme !== f.theme)
      return false;
    if (f.place !== null && !coversPlace(e, f.place, group)) return false;
    // A series still being updated (last_year null) reaches every later year.
    if (f.to !== null && e.first_year > f.to) return false;
    if (f.from !== null && e.last_year !== null && e.last_year < f.from)
      return false;
    if (words.length === 0) return true;
    const text = haystack(e);
    return words.every((w) => text.includes(w));
  });
}

/** The places the catalog names, for the place menu: groups, then countries. */
export function placeOptions(entries: readonly CatalogEntry[]): {
  groups: string[];
  countries: string[];
} {
  const groups = new Set<string>();
  const countries = new Set<string>();
  for (const e of entries) {
    e.groups.forEach((g) => groups.add(g));
    e.countries.forEach((c) => countries.add(c));
  }
  return { groups: [...groups].sort(), countries: [...countries].sort() };
}

/** The first and last year any series reaches; `last` is null while one is still updated. */
export function yearSpan(entries: readonly CatalogEntry[]): {
  first: number;
  last: number | null;
} | null {
  if (entries.length === 0) return null;
  const ongoing = entries.some((e) => e.last_year === null);
  return {
    first: Math.min(...entries.map((e) => e.first_year)),
    last: ongoing ? null : Math.max(...entries.map((e) => e.last_year ?? 0)),
  };
}

function year(value: string | null): number | null {
  if (value === null || !/^\d{4}$/.test(value)) return null;
  return Number(value);
}

/** The filter written in an address (`?q=rent&theme=prices&place=IT&from=2010&to=2020`). */
export function readFilter(
  params: { get(name: string): string | null },
  themes: readonly string[],
): CatalogFilter {
  const theme = params.get("theme");
  const place = params.get("place");
  return {
    q: params.get("q") ?? "",
    theme:
      theme !== null && themes.includes(theme)
        ? (theme as CatalogFilter["theme"])
        : null,
    place: place !== null && /^[A-Z]{2,5}$/.test(place) ? place : null,
    from: year(params.get("from")),
    to: year(params.get("to")),
  };
}

/** The query string for a filter, without the "?"; empty when nothing is asked. */
export function filterQuery(f: CatalogFilter): string {
  const out = new URLSearchParams();
  for (const key of KEYS) {
    const value = f[key];
    if (value !== null && String(value).trim() !== "")
      out.set(key, String(value));
  }
  return out.toString();
}
