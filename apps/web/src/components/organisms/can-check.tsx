import { ArrowRight } from "lucide-react";
import Link from "next/link";
import type { CatalogEntry } from "@/lib/api/client";
import { coverage } from "@/lib/catalog-stats";
import { sourceName } from "@/lib/format";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.home;

const names = new Intl.ListFormat("en", { style: "long", type: "conjunction" });

/**
 * One line on what HoldsUp can check, counted from the catalog, and a way to the
 * full list (the catalog page has the counts by source, the filters and the
 * search). Without a catalog (the API is down) it is a plain pointer.
 */
export function CanCheck({ entries }: { entries?: readonly CatalogEntry[] }) {
  const stats = coverage(entries ?? []);
  return (
    <section
      id="can-check"
      aria-label={t.canCheckHeading}
      className="glass flex flex-col gap-3 rounded-2xl p-5 sm:flex-row sm:items-center sm:justify-between sm:gap-6"
    >
      <p className="leading-7">
        {stats
          ? t.coverage.line(
              stats.statistics,
              stats.topics,
              names.format(stats.sources.map((s) => sourceName(s.id))),
              t.coverage.yearRange(stats.firstYear, stats.lastYear),
            )
          : t.canCheckBody}
      </p>
      <Link
        href={routes.indicators}
        className="text-brand inline-flex shrink-0 items-center gap-2 text-sm font-semibold hover:underline"
      >
        {t.canCheckLink}
        <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
      </Link>
    </section>
  );
}
