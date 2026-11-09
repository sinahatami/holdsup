"use client";

import { useUrlFilter, type FilterCodec } from "@/hooks/use-url-filter";
import {
  noRecentFilter,
  readRecentFilter,
  recentQuery,
  type RecentFilter,
} from "@/lib/recent-filter";
import { strings } from "@/lib/strings";

const verdicts = Object.keys(strings.verdicts);
const themes = Object.keys(strings.indicators.themes);

const codec: FilterCodec<RecentFilter> = {
  read: (params) => readRecentFilter(params, verdicts, themes),
  query: recentQuery,
  empty: noRecentFilter,
};

/** What the visitor has narrowed the recent checks down to, kept in the address. */
export function useRecentFilter() {
  return useUrlFilter(codec);
}
