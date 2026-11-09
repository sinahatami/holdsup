/** Every in-app link target, so a route change is one edit. */
export const routes = {
  home: "/",
  howItWorks: "/#how",
  // Until the methodology page exists (FRONTEND_TASKS 3.2), "how it works" is the
  // nearest explanation of how a verdict is reached. Point this at it then.
  methodology: "/#how",
  indicators: "/indicators",
  check: (id: string) => `/check/${id}`,
} as const;
