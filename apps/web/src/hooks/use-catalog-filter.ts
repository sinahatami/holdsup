"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  filterQuery,
  noFilter,
  readFilter,
  type CatalogFilter,
} from "@/lib/catalog-filter";
import { strings } from "@/lib/strings";

const themes = Object.keys(strings.indicators.themes);

/**
 * What the visitor has narrowed the catalog down to. It starts from the address, so a
 * link to a filtered list opens filtered, and it writes each change back to the address
 * (replacing the entry, so Back leaves the page instead of undoing every keystroke).
 * `version` changes when the filter is cleared, for inputs that keep their own text.
 */
export function useCatalogFilter() {
  const params = useSearchParams();
  const [filter, setFilter] = useState(() => readFilter(params, themes));
  const [version, setVersion] = useState(0);

  function apply(next: CatalogFilter) {
    setFilter(next);
    const query = filterQuery(next);
    const path = window.location.pathname;
    window.history.replaceState(null, "", query ? `${path}?${query}` : path);
  }

  return {
    filter,
    version,
    change: (patch: Partial<CatalogFilter>) => apply({ ...filter, ...patch }),
    clear: () => {
      setVersion((v) => v + 1);
      apply(noFilter);
    },
  };
}
