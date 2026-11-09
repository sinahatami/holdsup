import { TitledSection } from "@/components/molecules/titled-section";
import type { CatalogEntry } from "@/lib/api/client";
import { coverageText } from "@/lib/catalog-coverage";
import { strings } from "@/lib/strings";

type Theme = keyof typeof strings.indicators.themes;
const themeOrder = Object.keys(strings.indicators.themes) as Theme[];

/** Entries (already A to Z) split by theme, in the page's theme order; empty themes are dropped. */
function groupByTheme(entries: CatalogEntry[]) {
  return themeOrder
    .map((theme) => ({
      theme,
      entries: entries.filter((e) => e.theme === theme),
    }))
    .filter((g) => g.entries.length > 0);
}

function Detail({
  term,
  children,
}: {
  term: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <dt className="text-muted-foreground">{term}</dt>
      <dd>{children}</dd>
    </>
  );
}

/** One statistic: what it measures, where it comes from, the years it spans and the places it covers. */
function Entry({ entry: e }: { entry: CatalogEntry }) {
  const t = strings.indicators;
  return (
    <li className="glass rounded-2xl p-5">
      <h3 className="text-lg font-semibold">{e.name}</h3>
      <p className="mt-1 leading-7">{e.definition}</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <Detail term={t.source}>
          {e.source}{" "}
          <code className="bg-muted rounded px-1.5 py-0.5 text-xs break-all">
            {e.source_code}
          </code>
        </Detail>
        <Detail term={t.unitLabel}>{e.unit}</Detail>
        <Detail term={t.yearsLabel}>
          {t.years(e.first_year, e.last_year)}
        </Detail>
        <Detail term={t.coverageLabel}>{coverageText(e)}</Detail>
      </dl>
    </li>
  );
}

/** Statistics HoldsUp can check, grouped by theme (A to Z within each). */
export function CatalogList({ entries }: { entries: CatalogEntry[] }) {
  const groups = groupByTheme(entries);
  return (
    <div className="flex flex-col gap-12">
      {groups.map((g) => (
        <TitledSection
          key={g.theme}
          id={`theme-${g.theme}`}
          title={strings.indicators.themes[g.theme]}
          aside={strings.indicators.count(g.entries.length)}
          className="scroll-mt-24"
        >
          <ul className="flex flex-col gap-4">
            {g.entries.map((e) => (
              <Entry key={e.id} entry={e} />
            ))}
          </ul>
        </TitledSection>
      ))}
    </div>
  );
}
