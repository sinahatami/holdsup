import { FilterButton } from "@/components/atoms/filter-button";
import { fieldControl } from "@/components/atoms/field-control";
import { Field } from "@/components/molecules/field";
import type { GalleryItem, Label } from "@/lib/api/client";
import { placeName } from "@/lib/format";
import type { RecentFilter } from "@/lib/recent-filter";
import { strings } from "@/lib/strings";

type Theme = NonNullable<GalleryItem["claims"][number]["theme"]>;
const t = strings.recent;
const verdictOrder = Object.keys(strings.verdicts) as Label[];
const themeOrder = Object.keys(strings.indicators.themes) as Theme[];

/** The verdict and topic buttons and the place menu that narrow the recent checks. */
export function RecentFilters({
  filter,
  places,
  verdictCounts,
  themeCounts,
  total,
  onChange,
}: {
  filter: RecentFilter;
  /** The places the checks are about, as codes. */
  places: string[];
  /** How many checks each verdict, and each topic, would show under the other filters. */
  verdictCounts: Record<Label, number>;
  themeCounts: Record<Theme, number>;
  /** How many checks match everything but the verdict, for the "all" button. */
  total: { verdict: number; theme: number };
  onChange: (patch: Partial<RecentFilter>) => void;
}) {
  const options = [
    ...new Set([...places, ...(filter.place ? [filter.place] : [])]),
  ]
    .map((code) => ({ code, name: placeName(code) }))
    .sort((a, b) => a.name.localeCompare(b.name, "en"));
  return (
    <form
      role="search"
      aria-label={t.filtersHeading}
      onSubmit={(e) => e.preventDefault()}
      className="glass flex flex-col gap-5 rounded-3xl p-5 sm:p-6"
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">{t.verdict}</legend>
        <div className="flex flex-wrap gap-2">
          <FilterButton
            pressed={filter.verdict === null}
            count={total.verdict}
            onClick={() => onChange({ verdict: null })}
          >
            {t.allVerdicts}
          </FilterButton>
          {verdictOrder.map((verdict) => {
            const pressed = filter.verdict === verdict;
            return (
              <FilterButton
                key={verdict}
                pressed={pressed}
                count={verdictCounts[verdict]}
                disabled={verdictCounts[verdict] === 0 && !pressed}
                onClick={() => onChange({ verdict: pressed ? null : verdict })}
              >
                {strings.verdicts[verdict]}
              </FilterButton>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">{t.topic}</legend>
        <div className="flex flex-wrap gap-2">
          <FilterButton
            pressed={filter.theme === null}
            count={total.theme}
            onClick={() => onChange({ theme: null })}
          >
            {t.allTopics}
          </FilterButton>
          {themeOrder.map((theme) => {
            const pressed = filter.theme === theme;
            return (
              <FilterButton
                key={theme}
                pressed={pressed}
                count={themeCounts[theme]}
                disabled={themeCounts[theme] === 0 && !pressed}
                onClick={() => onChange({ theme: pressed ? null : theme })}
              >
                {strings.indicators.themes[theme]}
              </FilterButton>
            );
          })}
        </div>
      </fieldset>

      <Field label={t.place} htmlFor="recent-place" className="sm:max-w-xs">
        <select
          id="recent-place"
          value={filter.place ?? ""}
          onChange={(e) => onChange({ place: e.target.value || null })}
          className={fieldControl}
        >
          <option value="">{t.anyPlace}</option>
          {options.map((o) => (
            <option key={o.code} value={o.code}>
              {o.name}
            </option>
          ))}
        </select>
      </Field>
    </form>
  );
}
