// The error pages' text, kept apart from `strings`: global-error.tsx is loaded on every page,
// and importing `strings` there put a second copy of all of it in the browser.
export const boundaryStrings = {
  locale: "en",
  dir: "ltr",
  error: {
    heading: "Something went wrong",
    body: "HoldsUp hit an unexpected problem. Trying again often fixes it.",
    retry: "Try again",
  },
  back: "Check another claim",
} as const;
