import { useState } from "react";
import { fieldControl } from "@/components/atoms/field-control";
import { FilterButton } from "@/components/atoms/filter-button";
import { Field } from "@/components/molecules/field";
import type { CatalogEntry } from "@/lib/api/client";
import {
  placeOptions,
  yearsBackwards,
  type CatalogFilter,
} from "@/lib/catalog-filter";
import { placeName } from "@/lib/format";
import { strings } from "@/lib/strings";

type Theme = CatalogEntry["theme"];
const t = strings.indicators;
const themeOrder = Object.keys(t.themes) as Theme[];

const YEAR_HINT_ID = "catalog-years-hint";
const YEAR_ERROR_ID = "catalog-years-error";

/** A four-digit year box: it keeps what is typed and only reports a whole year, or nothing. */
function YearInput({
  id,
  label,
  value,
  invalid,
  onCommit,
}: {
  id: string;
  label: string;
  value: number | null;
  invalid: boolean;
  onCommit: (year: number | null) => void;
}) {
  const [text, setText] = useState(value === null ? "" : String(value));
  return (
    <Field label={label} htmlFor={id}>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        maxLength={4}
        value={text}
        aria-invalid={invalid || undefined}
        aria-describedby={
          invalid ? `${YEAR_HINT_ID} ${YEAR_ERROR_ID}` : YEAR_HINT_ID
        }
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, "").slice(0, 4);
          setText(digits);
          if (digits === "") onCommit(null);
          else if (digits.length === 4) onCommit(Number(digits));
        }}
        className={fieldControl}
      />
    </Field>
  );
}

/** Country names for the place menu, A to Z by name; the filter's own place is kept even if no entry names it. */
function countryOptions(
  codes: string[],
  current: string | null,
  groups: string[],
) {
  const all = new Set(codes);
  if (current && !groups.includes(current)) all.add(current);
  return [...all]
    .map((code) => ({ code, name: placeName(code) }))
    .sort((a, b) => a.name.localeCompare(b.name, "en"));
}

/** The search box, topic buttons, place menu and year range that narrow the catalog. */
export function CatalogFilters({
  entries,
  filter,
  themeCounts,
  version,
  onChange,
}: {
  entries: CatalogEntry[];
  filter: CatalogFilter;
  /** How many entries each topic would show under the other filters. */
  themeCounts: Record<Theme, number>;
  /** Changes when the filter is cleared, to reset the year boxes' own text. */
  version: number;
  onChange: (patch: Partial<CatalogFilter>) => void;
}) {
  const places = placeOptions(entries);
  const backwards = yearsBackwards(filter);
  const total = themeOrder.reduce((n, k) => n + themeCounts[k], 0);

  return (
    <form
      role="search"
      aria-label={t.filtersHeading}
      onSubmit={(e) => e.preventDefault()}
      className="glass flex flex-col gap-5 rounded-3xl p-5 sm:p-6"
    >
      <Field label={t.search} htmlFor="catalog-q">
        <input
          id="catalog-q"
          type="search"
          autoComplete="off"
          value={filter.q}
          placeholder={t.searchPlaceholder}
          onChange={(e) => onChange({ q: e.target.value })}
          className={fieldControl}
        />
      </Field>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">{t.topic}</legend>
        <div className="flex flex-wrap gap-2">
          <FilterButton
            pressed={filter.theme === null}
            count={total}
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
                {t.themes[theme]}
              </FilterButton>
            );
          })}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t.place}
          htmlFor="catalog-place"
          hint={t.placeNote}
          hintId="catalog-place-note"
        >
          <select
            id="catalog-place"
            value={filter.place ?? ""}
            aria-describedby="catalog-place-note"
            onChange={(e) => onChange({ place: e.target.value || null })}
            className={fieldControl}
          >
            <option value="">{t.anyPlace}</option>
            {places.groups.length > 0 && (
              <optgroup label={t.placeGroups}>
                {places.groups.map((code) => (
                  <option key={code} value={code}>
                    {placeName(code)}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label={t.placeCountries}>
              {countryOptions(
                places.countries,
                filter.place,
                places.groups,
              ).map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          </select>
        </Field>

        <fieldset className="flex flex-col gap-1.5">
          <legend className="sr-only">{t.yearsLegend}</legend>
          <div className="grid grid-cols-2 gap-3" key={version}>
            <YearInput
              id="catalog-from"
              label={t.fromYear}
              value={filter.from}
              invalid={backwards}
              onCommit={(from) => onChange({ from })}
            />
            <YearInput
              id="catalog-to"
              label={t.toYear}
              value={filter.to}
              invalid={backwards}
              onCommit={(to) => onChange({ to })}
            />
          </div>
          <p id={YEAR_HINT_ID} className="text-muted-foreground text-xs">
            {t.yearHint}
          </p>
          {backwards && (
            <p
              id={YEAR_ERROR_ID}
              role="alert"
              className="text-destructive text-sm font-medium"
            >
              {t.yearsBackwards}
            </p>
          )}
        </fieldset>
      </div>
    </form>
  );
}
