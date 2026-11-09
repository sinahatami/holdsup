"use client";

import { useUrlFilter, type FilterCodec } from "@/hooks/use-url-filter";
import {
  filterQuery,
  noFilter,
  readFilter,
  type CatalogFilter,
} from "@/lib/catalog-filter";
import { strings } from "@/lib/strings";

const themes = Object.keys(strings.indicators.themes);

const codec: FilterCodec<CatalogFilter> = {
  read: (params) => readFilter(params, themes),
  query: filterQuery,
  empty: noFilter,
};

/** What the visitor has narrowed the catalog down to, kept in the address. */
export function useCatalogFilter() {
  return useUrlFilter(codec);
}
