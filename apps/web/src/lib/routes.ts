/** Every in-app link target, so a route change is one edit. */
export const routes = {
  home: "/",
  methodology: "/methodology",
  about: "/about",
  indicators: "/indicators",
  recent: "/recent",
  status: "/status",
  cannotCheck: "/methodology#cannot",
  /** The catalog narrowed to a word or two, as the catalog page reads it. */
  indicatorSearch: (q: string) => `/indicators?q=${encodeURIComponent(q)}`,
  check: (id: string) => `/check/${id}`,
  /** The check's share card, the picture a shared link shows. */
  checkImage: (id: string) => `/check/${id}/opengraph-image`,
} as const;
