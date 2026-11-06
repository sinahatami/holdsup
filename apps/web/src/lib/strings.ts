// All interface text lives here (RTL/i18n readiness; see CLAUDE.md conventions).
export const strings = {
  locale: "en",
  dir: "ltr",
  appName: "HoldsUp",
  tagline: "Every number has a denominator.",
  metaDescription:
    "HoldsUp checks numeric claims against official statistics and shows its work.",
  home: {
    intro:
      "Paste a sentence with a number in it. HoldsUp finds the official series, recomputes the claim, and tells you whether it holds up.",
    comingSoon: "Claim checking is coming soon.",
  },
} as const;
