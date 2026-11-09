import type { CatalogEntry } from "@/lib/api/client";
import { placeName } from "@/lib/format";
import { strings } from "@/lib/strings";

/** Where an entry has data, in a few words: "27 countries and the EU as a whole". */
export function coverageText(e: CatalogEntry): string {
  const t = strings.indicators.coverage;
  const parts: string[] = [];
  if (e.all_countries) parts.push(t.everyCountry);
  else if (e.countries.length > 3) parts.push(t.countries(e.countries.length));
  else parts.push(...e.countries.map(placeName));
  parts.push(...e.groups.map((g) => t.group[g] ?? placeName(g)));
  const text = new Intl.ListFormat("en", { type: "conjunction" }).format(parts);
  return text.charAt(0).toUpperCase() + text.slice(1);
}
