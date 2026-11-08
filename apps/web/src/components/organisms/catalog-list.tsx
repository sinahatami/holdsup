import { pill } from "@/components/atoms/pill";
import { TitledSection } from "@/components/molecules/titled-section";
import type { CatalogEntry } from "@/lib/api/client";
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

/** Every statistic HoldsUp can check, grouped by theme and A to Z within each: what it measures, its unit and where it comes from. */
export function CatalogList({ entries }: { entries: CatalogEntry[] }) {
  const groups = groupByTheme(entries);
  return (
    <section aria-label={strings.indicators.heading}>
      <p className="text-muted-foreground mb-4 text-sm">
        {strings.indicators.count(entries.length)}
      </p>
      <nav aria-label={strings.indicators.themesNav} className="mb-10">
        <ul className="flex flex-wrap gap-2">
          {groups.map((g) => (
            <li key={g.theme}>
              <a href={`#theme-${g.theme}`} className={pill({ tone: "glass" })}>
                {strings.indicators.themes[g.theme]}
                <span className="text-muted-foreground">
                  {g.entries.length}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
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
                <li key={e.id} className="glass rounded-2xl p-5">
                  <h3 className="text-lg font-semibold">{e.name}</h3>
                  <p className="mt-1 leading-7">{e.definition}</p>
                  <p className="text-muted-foreground mt-2 text-sm">
                    {e.unit} · {e.source} ·{" "}
                    {strings.indicators.years(e.first_year, e.last_year)}
                  </p>
                </li>
              ))}
            </ul>
          </TitledSection>
        ))}
      </div>
    </section>
  );
}
