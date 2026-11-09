import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { TitledSection } from "@/components/molecules/titled-section";
import type { CatalogEntry } from "@/lib/api/client";
import { coverage } from "@/lib/catalog-stats";
import { sourceName } from "@/lib/format";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.home;

/** The label comes first in the markup (a term before its description) and the number first on screen. */
function Tile({ value, label }: { value: string; label: string }) {
  return (
    <div className="glass flex flex-col-reverse gap-1 rounded-2xl p-4">
      <dt className="text-muted-foreground text-sm">{label}</dt>
      <dd className="text-xl font-bold tracking-tight whitespace-nowrap tabular-nums sm:text-2xl">
        {value}
      </dd>
    </div>
  );
}

/**
 * Home-page summary of what HoldsUp can check, counted from the catalog: how
 * many statistics, topics and sources, the years they span, and who publishes
 * them. Without a catalog (the API is down) it falls back to a plain pointer.
 */
export function CanCheck({ entries }: { entries?: readonly CatalogEntry[] }) {
  const stats = coverage(entries ?? []);
  return (
    <TitledSection id="can-check" title={t.canCheckHeading}>
      <p className="text-muted-foreground leading-7">
        {stats ? t.coverage.intro : t.canCheckBody}
      </p>
      {stats && (
        <>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Tile
              value={stats.statistics.toLocaleString()}
              label={t.coverage.statistics(stats.statistics)}
            />
            <Tile
              value={stats.topics.toLocaleString()}
              label={t.coverage.topics(stats.topics)}
            />
            <Tile
              value={stats.sources.length.toLocaleString()}
              label={t.coverage.sources(stats.sources.length)}
            />
            <Tile
              value={t.coverage.yearRange(stats.firstYear, stats.lastYear)}
              label={t.coverage.years}
            />
          </dl>
          <div className="flex flex-col gap-2">
            <h3 className="text-muted-foreground text-sm font-medium">
              {t.coverage.sourcesHeading}
            </h3>
            <ul className="flex flex-wrap gap-2">
              {stats.sources.map((s) => (
                <li
                  key={s.id}
                  className="glass flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium"
                >
                  {sourceName(s.id)}
                  <span className="text-muted-foreground tabular-nums">
                    {s.count}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
      <Link
        href={routes.indicators}
        className="text-brand inline-flex items-center gap-2 text-sm font-semibold hover:underline"
      >
        {t.canCheckLink}
        <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
      </Link>
    </TitledSection>
  );
}
