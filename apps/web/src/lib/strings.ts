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
  // The claim spec's place codes that are not countries; the browser names the countries.
  places: {
    EU: "European Union",
    EA: "Euro area",
    WORLD: "World",
    G7: "G7",
    G20: "G20",
    OECD: "OECD",
  },
  periods: {
    latest: "the latest period",
    quarter: (q: string, year: string) => `Q${q} ${year}`,
    half: (h: string, year: string) =>
      h === "1" ? `the first half of ${year}` : `the second half of ${year}`,
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
    shortcut: "to check",
    charsLeft: (n: string) => `${n} left`,
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
    neutrality: {
      text: "A verdict is about the number, not about the person who said it.",
      link: "How HoldsUp judges a claim",
    },
    maxChars: 2000,
    tooLong: "Please keep the text under 2,000 characters.",
  },
  check: {
    heading: "Check",
    traceHeading: "What HoldsUp is doing",
    // Names each claim's section for a screen reader; "Claim" alone when there is one.
    claimOf: (n: number, total: number) =>
      total > 1 ? `Claim ${n} of ${total}` : "Claim",
    originalHeading: "The text you checked",
    explanationHeading: "Why",
    loading: "Loading the check…",
    connectionLost:
      "Lost the connection to the live trace. Reload to try again.",
    errorHeading: "This check could not be completed",
    retryAfter: (s: number) => `Try again in about ${s} seconds.`,
    cached: "Answered from an earlier check of the same claim.",
    cachedLink: "See that check",
    back: "Check another claim",
    noClaims:
      "HoldsUp found no claim with a number in it. Try a sentence such as “Italy's unemployment rate fell to 7.7% in 2023.”",
    closestHeading: "The closest things HoldsUp can check",
    seeAll: "See everything HoldsUp can check",
    missing: {
      heading: "No check at this link",
      body: "The link may be wrong or cut short. Every check has its own full link; if you have the claim, you can check it again.",
    },
    // The page title and the shared preview: how it came out, then what was said.
    metaTitle: (verdict: string, claim: string) => `${verdict} · “${claim}”`,
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
  legend: {
    heading: "What the verdicts mean",
    onThisPage: "On this page",
    // The framing threshold comes with each result; without one the rule is said without a number.
    holds: (pct: number | null) =>
      `Every figure in the claim is within the allowed gap of the official figure, and the claim holds ${
        pct === null
          ? "across most comparable time windows"
          : `in at least ${pct}% of comparable time windows`
      }.`,
    framing: (pct: number | null) =>
      `The figures are within the allowed gap, but the claim holds in ${
        pct === null ? "too few" : `fewer than ${pct}% of`
      } comparable time windows, or fails a check for misleading framing.`,
    partly:
      "The claim has several parts, and some are within the allowed gap while others are not.",
    fails:
      "The figures are outside the allowed gap for the period the claim names.",
    cant: "There is no confident match to an official statistic, no data for the place or period, or the claim is not one HoldsUp can check yet.",
    gapHeading: "The allowed gap",
    gap: "How far the official figure may be from the one claimed and still count as a match. It depends on the kind of claim: a figure stated as a level allows for rounding and a small margin for later data revisions, a change allows a few per cent, and a position in a ranking allows none. Each figure's own gap is listed in its receipt above.",
    version: (n: number) => `Tolerances version ${n}.`,
    method: "How HoldsUp judges a claim",
  },
  receipt: {
    heading: "Receipt",
    intro: "Everything behind this verdict, so you can check it yourself.",
    opensInNewTab: "(opens in a new tab)",
    reading: {
      heading: "How HoldsUp read the claim",
      statistic: "Statistic",
      place: "Place",
      comparedWith: "Compared with",
      period: "Period",
      periodRange: (from: string, to: string) => `${from} to ${to}`,
      periodFrom: (from: string) => `from ${from}`,
      kind: "Kind of claim",
      direction: "Direction",
      figure: "Figure stated",
      range: "From, to",
      startsAt: "Starts at",
      endsAt: "Ends at",
      saidBy: "Said by",
      start: "start",
      end: "end",
      // How a value came to be, when it was not simply written in the claim.
      basis: {
        inferred: "inferred from the context",
        lookback: "counted back from when it was said",
        office: "taken from the speaker's term of office",
        assumed: "assumed, because the claim says “for years” or “recently”",
      },
      kinds: {
        level: "A stated level",
        absolute: "A change in amount",
        percent: "A percentage change",
        percentage_points: "A change in percentage points",
        ratio: "A ratio, such as “halved”",
        trend: "A trend",
        record: "A record",
        rank: "A rank",
        compare: "A comparison with other places",
        target: "A target",
        streak: "A streak",
      },
      directions: { up: "Up", down: "Down", flat: "Flat" },
      operators: {
        about: "",
        more_than: "more than",
        less_than: "less than",
        at_least: "at least",
        at_most: "at most",
      },
    },
    series: {
      heading: "The official series",
      statistic: "Statistic",
      measures: "What it measures",
      unit: "Unit",
      frequency: "Frequency",
      publisher: "Published by",
      dataset: "Dataset",
      data: "Raw data",
      openData: "Open the data",
      updated: "Last updated by the source",
      retrieved: "Retrieved by HoldsUp",
      citation: "Cite as",
      whyMatched: "Why this series",
      alsoConsidered: "Also considered",
      alsoUsed: "Also used",
      noData: "No data was fetched for this claim.",
    },
    recompute: {
      heading: "How it was recomputed",
      valuesFrom: "The figures in these steps come from",
      step: (n: number) => `Step ${n}`,
      decides: "Decides the verdict",
      figuresUsed: "Figures used",
      result: "Result",
      note: "Note",
      // What each calculation does, in words. Keys are the API's operation names.
      ops: {
        value_at: (place: string, when: string) =>
          `Look up the value for ${place} in ${when}.`,
        change: {
          absolute: (from: string, to: string) =>
            `Take the value for ${from} away from the value for ${to}.`,
          percent: (from: string, to: string) =>
            `Take the value for ${from} away from the value for ${to}, divide by the value for ${from}, and multiply by 100.`,
          percentage_points: (from: string, to: string) =>
            `Take the rate for ${from} away from the rate for ${to}.`,
          ratio: (from: string, to: string) =>
            `Divide the value for ${to} by the value for ${from}.`,
        },
        cagr: (from: string, to: string) =>
          `Work out the yearly growth rate that takes the value from ${from} to ${to}.`,
        trend: (from: string, to: string) =>
          `Fit a straight line through the values from ${from} to ${to} and read its slope per year.`,
        compare: (place: string, other: string, when: string) =>
          `Take the value for ${other} away from the value for ${place} in ${when}.`,
        rank: (place: string, when: string) =>
          `Order the places by their value in ${when} and find the position of ${place}.`,
        per_capita: "Divide each value by the population for the same period.",
        deflate: (base: string) =>
          `Restate each value in the prices of ${base}, using the price index.`,
      },
    },
    compared: {
      heading: "What the verdict compared",
      intro:
        "The figure in the claim beside the official figure, and how far apart they may be and still count as a match.",
      claimed: "Claimed",
      official: "Official",
      gap: "Allowed gap",
      holds: "Holds",
      fails: "Does not hold",
      directionOnly: "Only the direction is compared.",
      directions: { up: "up", down: "down", flat: "flat" },
      // The names the API gives each compared part ("assertion", "start value", "vs FR").
      parts: {
        assertion: "The claim itself",
        "start value": "Start value",
        "end value": "End value",
        against: (place: string) => `Against ${place}`,
      },
    },
    verify: {
      heading: "How to verify it yourself",
      open: "Open the data.",
      openBody:
        "It is the exact request HoldsUp made, so it returns the same series.",
      find: "Find the figures.",
      findBody:
        "Look up each place and period listed under “How it was recomputed” and check the values match.",
      revised: (source: string, date: string) =>
        `If ${source} has revised the series since ${date}, small differences are expected.`,
      repeat: "Repeat the calculation.",
      repeatBody:
        "Each step says what to do; a calculator or a spreadsheet is enough.",
      compare: "Compare with the claim.",
      compareBody: "The result should fall within the allowed gap shown above.",
    },
    technical: {
      heading: "Technical details",
      fingerprint: "Data fingerprint (SHA-256)",
      observations: "Observations with a value",
      models: "Models used",
      versions: "Versions",
      app: "app",
      catalog: "catalog",
      tolerances: "tolerances",
    },
  },
} as const;
