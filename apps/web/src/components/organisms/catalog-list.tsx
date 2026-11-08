import type { CatalogEntry } from "@/lib/api/client";
import { strings } from "@/lib/strings";

/** Every statistic HoldsUp can check, A to Z: what it measures, its unit and where it comes from. */
export function CatalogList({ entries }: { entries: CatalogEntry[] }) {
  return (
    <section aria-label={strings.indicators.heading}>
      <p className="text-muted-foreground mb-4 text-sm">
        {strings.indicators.count(entries.length)}
      </p>
      <ul className="flex flex-col gap-4">
        {entries.map((e) => (
          <li key={e.id} className="glass rounded-2xl p-5">
            <h2 className="text-lg font-semibold">{e.name}</h2>
            <p className="mt-1 leading-7">{e.definition}</p>
            <p className="text-muted-foreground mt-2 text-sm">
              {e.unit} · {e.source} ·{" "}
              {strings.indicators.years(e.first_year, e.last_year)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
