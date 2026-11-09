// All interface text lives here (RTL/i18n readiness; see CLAUDE.md conventions).
export const strings = {
  locale: "en",
  dir: "ltr",
  appName: "HoldsUp",
  tagline: "Every number has a denominator.",
  metaDescription:
    "HoldsUp checks numeric claims against official statistics and shows its work.",
  errors: {
    network: "Network error",
  },
  // Display names for the API's source ids; an unknown id is shown as it is.
  sources: {
    eurostat: "Eurostat",
    worldbank: "World Bank",
    owid: "Our World in Data",
  },
  nav: {
    main: "Main",
    home: "Home",
    howItWorks: "How it works",
    canCheck: "What it can check",
    recent: "Recent checks",
    theme: "Theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
  },
  footer: {
    blurb:
      "Numeric claims, checked against official statistics, with the receipts.",
    github: "View on GitHub",
    repoUrl: "https://github.com/sinahatami/holdsup",
    note: "Open source. Data from official statistical agencies.",
    copyright: "© 2026",
  },
  notFound: {
    code: "404",
    heading: "Page not found",
    body: "That page doesn't exist, but there are plenty of claims left to check.",
  },
  home: {
    howHeading: "How it works",
    howExampleLabel: "In the sample above",
    how: [
      {
        title: "Paste a claim",
        body: "Any sentence with a number in it. HoldsUp picks out each claim: the place, the period and the figure.",
        example: "Italy, 2015 to 2023, from 11.9% to 7.7%",
      },
      {
        title: "We match it to an official series",
        body: "Each claim is matched to one published statistic, and its data is fetched from the source, such as Eurostat or the World Bank.",
        example: "Unemployment rate (monthly), Eurostat",
      },
      {
        title: "We recompute it, you check our work",
        body: "Plain code, not a language model, does the arithmetic. The receipt lists every figure, calculation, source link and data fingerprint.",
        example: "12.02% to 7.68%, down 4.34 points",
      },
    ],
    intro:
      "Paste a sentence with a number in it. HoldsUp finds the official series, recomputes the claim, and tells you whether it holds up.",
    inputLabel: "The claim to check",
    placeholder:
      "e.g. Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
    submit: "Check this claim",
    submitting: "Sending…",
    sample: {
      heading: "A sample receipt",
      open: "Open the full receipt",
      claimLabel: "Claim",
      claim:
        "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
      seriesLabel: "Official series",
      series: "Unemployment rate (monthly)",
      source: "Eurostat · une_rt_m",
      recomputedLabel: "Recomputed",
      recomputed: "12.02% → 7.68%",
      recomputedNote: "Down 4.34 points (yearly averages)",
      verdictLabel: "Verdict",
      verdict: "supported",
    },
    examplesHeading: "Try an example",
    examples: [
      "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
      "Italy's public debt is 133% of GDP.",
      "Youth unemployment in Italy has risen every year since 2008.",
    ],
    canCheckHeading: "What HoldsUp can check",
    canCheckBody:
      "Every claim is matched to an official statistic. Browse the full list to see which topics, sources and years are covered.",
    canCheckLink: "See everything HoldsUp can check",
    coverage: {
      intro:
        "Every claim is matched to an official statistic. This is what is covered today.",
      statistics: (n: number) => (n === 1 ? "statistic" : "statistics"),
      topics: (n: number) => (n === 1 ? "topic" : "topics"),
      sources: (n: number) => (n === 1 ? "source" : "sources"),
      years: "oldest series to now",
      yearRange: (first: number, last: number | null) =>
        last === null ? `${first}–now` : `${first}–${last}`,
      sourcesHeading: "Data comes from",
    },
    galleryHeading: "Recent checks",
    galleryEmpty: "No checks have been featured yet.",
    card: {
      claimed: "Claimed",
      official: "official",
      checkedAgainst: (indicator: string) => `Checked against ${indicator}`,
      noFigure: "No official figure to compare.",
      summary: (holds: number, total: number) =>
        `${holds} of ${total} claims hold up`,
    },
    maxChars: 2000,
    tooLong: "Please keep the text under 2,000 characters.",
  },
  check: {
    heading: "Check",
    traceHeading: "What HoldsUp is doing",
    claimHeading: "Claim",
    explanationHeading: "Why",
    loading: "Loading the check…",
    connectionLost:
      "Lost the connection to the live trace. Reload to try again.",
    errorHeading: "This check could not be completed",
    retryAfter: (s: number) => `Try again in about ${s} seconds.`,
    cached: "Answered from an earlier check of the same claim.",
    back: "Check another claim",
    noClaims:
      "HoldsUp found no claim with a number in it. Try a sentence such as “Italy's unemployment rate fell to 7.7% in 2023.”",
    closestHeading: "The closest things HoldsUp can check",
    seeAll: "See everything HoldsUp can check",
  },
  indicators: {
    heading: "What HoldsUp can check",
    intro:
      "Each of these comes from an official source. A claim can be checked when it is about one of them.",
    unavailable:
      "The list could not be loaded just now. Please try again in a few minutes.",
    years: (first: number, last: number | null) =>
      last === null ? `since ${first}` : `${first} to ${last}`,
    count: (n: number) => (n === 1 ? "1 statistic" : `${n} statistics`),
    themesNav: "Jump to a topic",
    // Listed in this order on the page. Keys are the API's `theme` values.
    themes: {
      population: "Population",
      economy: "Economy",
      work: "Work and pay",
      prices: "Prices and housing",
      poverty: "Poverty and inequality",
      health: "Health",
      education: "Education",
      environment: "Environment",
      safety: "Safety",
    },
  },
  steps: {
    ledger: "Looking for an earlier check",
    extract: "Reading the claims",
    match: "Finding the official indicator",
    fetch: "Fetching the data",
    plan: "Planning the calculation",
    execute: "Running the calculation",
    verdict: "Weighing the result",
    explain: "Writing the explanation",
  },
  stepState: {
    running: "running",
    ok: "done",
    cant_check: "could not be checked",
  },
  verdicts: {
    supported: "Holds up",
    supported_framing_matters: "Holds up, but the framing matters",
    not_supported: "Does not hold up",
    partly_supported: "Partly holds up",
    cant_check: "Can't check",
  },
  receipt: {
    heading: "Receipt",
    indicator: "Indicator",
    definition: "Definition",
    source: "Source",
    dataset: "Dataset",
    retrieved: "Retrieved",
    fingerprint: "Data fingerprint (SHA-256)",
    operations: "Calculations",
    computed: "Computed",
    asserted: "Claimed",
    versions: "Versions",
    models: "Models used",
    alsoUsed: "Also used",
    app: "app",
    catalog: "catalog",
    tolerances: "tolerances",
    noData: "No data was fetched for this claim.",
    result: "result",
    note: "Note",
  },
} as const;
