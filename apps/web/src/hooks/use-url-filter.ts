"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

/** How a filter is written to, and read back from, an address's query string. */
export interface FilterCodec<T> {
  read(params: { get(name: string): string | null }): T;
  /** The query string for a filter, without the "?"; empty when nothing is asked. */
  query(filter: T): string;
  empty: T;
}

/**
 * What a visitor has narrowed a list down to. It starts from the address, so a link to a
 * filtered list opens filtered, and it writes each change back to the address (replacing
 * the entry, so Back leaves the page instead of undoing every keystroke). `version`
 * changes when the filter is cleared, for inputs that keep their own text.
 */
export function useUrlFilter<T extends object>(codec: FilterCodec<T>) {
  const params = useSearchParams();
  const [filter, setFilter] = useState(() => codec.read(params));
  const [version, setVersion] = useState(0);

  function apply(next: T) {
    setFilter(next);
    const query = codec.query(next);
    const path = window.location.pathname;
    window.history.replaceState(null, "", query ? `${path}?${query}` : path);
  }

  return {
    filter,
    version,
    change: (patch: Partial<T>) => apply({ ...filter, ...patch }),
    clear: () => {
      setVersion((v) => v + 1);
      apply(codec.empty);
    },
  };
}
