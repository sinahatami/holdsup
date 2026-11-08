/** Every in-app link target, so a route change is one edit. */
export const routes = {
  home: "/",
  howItWorks: "/#how",
  indicators: "/indicators",
  check: (id: string) => `/check/${id}`,
} as const;
