// All interface text lives here (RTL/i18n readiness).
export const strings = {
  locale: "en",
  dir: "ltr",
  appName: "HoldsUp",
  tagline: "Every number has a denominator.",
  metaDescription:
    "HoldsUp checks numeric claims against official statistics and shows its work.",
  errors: {
    network:
      "HoldsUp could not be reached. Check your connection and try again.",
    timeout: "HoldsUp took too long to answer. Please try again.",
  },
  problem: {
    heading: {
      network: "Could not reach HoldsUp",
      timeout: "HoldsUp took too long",
      rate_limited: "Too many checks for now",
      unavailable: "HoldsUp could not finish this check",
      other: "This check could not be completed",
    },
    retry: "Try again",
    retryIn: (s: number) => `Try again in ${s} s`,
    offline: {
      heading: "You are offline",
      body: "Pages and checks that need HoldsUp will not load until your connection is back.",
    },
    reconnect: "Reconnect",
  },
  error: {
    heading: "Something went wrong",
    body: "HoldsUp hit an unexpected problem. Trying again often fixes it.",
    retry: "Try again",
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
  voice: {
    start: "Speak",
    stop: "Stop",
    /** The one language it listens for. */
    lang: "en-US",
    listening: "Listening. Say the claim in English.",
    privacy:
      "Your browser's speech service turns your voice into text and may send the audio to its provider. HoldsUp only receives the text you submit.",
    review: (submit: string) =>
      `Check that every figure was heard correctly, then press “${submit}”.`,
    problems: {
      denied:
        "The microphone is blocked. Allow it for this site in your browser's settings, or type the claim.",
      silent: "Nothing was heard. Press Speak and try again.",
      noMic: "No microphone was found. Type the claim instead.",
      offline:
        "Voice input needs a connection to your browser's speech service. Type the claim instead.",
      other: "Voice input did not work. Type the claim instead.",
    },
  },
  nav: {
    main: "Main",
    home: "Home",
    canCheck: "What it can check",
    methodology: "Methodology",
    about: "About",
    recent: "Recent checks",
    status: "Status",
    pages: "Pages",
    menuOpen: "Open the menu",
    menuClose: "Close the menu",
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
    licenseUrl: "https://github.com/sinahatami/holdsup/blob/main/LICENSE",
    issuesUrl: "https://github.com/sinahatami/holdsup/issues",
    explore: "Explore",
    project: "Project",
    license: "MIT license",
    report: "Report a problem",
    note: "Verdicts are about the number, not the speaker.",
    legal: "MIT licensed, open source.",
  },
  notFound: {
    code: "404",
    heading: "Page not found",
    body: "That page doesn't exist, but there are plenty of claims left to check.",
    orTry: "Or look at",
  },
  history: {
    heading: "Your recent checks",
    note: "Kept in this browser only. Clearing your browser data removes them.",
    clear: "Clear the list",
    remove: (text: string) => `Remove from your list: ${text}`,
    summary: (holds: number, total: number) =>
      `${holds} of ${total} claims hold up`,
    running: "Result not seen yet",
  },
  home: {
    howHeading: "How it works",
    howMore: "Read the full method",
    // Short on purpose: the sample receipt shows the figures, the methodology page the detail.
    how: [
      {
        title: "Paste a claim",
        body: "Any sentence with a number in it. HoldsUp picks out the place, the period and the figure.",
      },
      {
        title: "We match an official series",
        body: "Each claim is matched to one published statistic, such as Eurostat's.",
      },
      {
        title: "We recompute it, you check",
        body: "Plain code does the arithmetic. The receipt lists every source and step.",
      },
    ],
    intro:
      "Paste a sentence with a number in it. HoldsUp finds the official series, recomputes the claim, and tells you whether it holds up.",
    inputLabel: "The claim to check",
    // One short line under the label. It says "speak" only where the Speak button is shown.
    helper: "Type a claim. English only for now.",
    helperVoice: "Type or speak a claim. English only for now.",
    placeholder:
      "e.g. Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
    submit: "Check this claim",
    submitting: "Sending…",
    shortcut: "to check",
    charsLeft: (n: string) => `${n} left`,
    sample: {
      heading: "Example receipt",
      note: "A fixed example of what a check returns, not a live check.",
      open: "View full receipt",
      claimLabel: "Claim",
      // The whole sentence. The home page looks for a real check with exactly this text to link to.
      claim:
        "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
      // Short on purpose: four equal columns leave about 150px each, so each holds a figure and one line.
      claimed: { from: "11.9%", to: "7.7%" },
      claimNote: "Italy, 2015 to 2023",
      seriesLabel: "Official series",
      series: "Unemployment rate",
      source: "Eurostat · une_rt_m",
      recomputedLabel: "Recomputed",
      recomputed: { from: "12.02%", to: "7.68%" },
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
      // One line; the catalog page has the full list, filters and sources.
      line: (
        statistics: number,
        topics: number,
        sources: string,
        years: string,
      ) =>
        `${statistics.toLocaleString()} official ${statistics === 1 ? "statistic" : "statistics"} on ${topics.toLocaleString()} ${topics === 1 ? "topic" : "topics"}, from ${sources}, ${years}.`,
      yearRange: (first: number, last: number | null) =>
        last === null ? `${first} to now` : `${first} to ${last}`,
    },
    galleryHeading: "Recent checks",
    galleryEmpty: "No checks have been featured yet.",
    galleryUnavailable:
      "Recent checks could not be loaded just now. Please try again in a few minutes.",
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
    connectionLost: "Lost the connection to the live trace.",
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
  // The series chart (P3.5): the data the check read, the claim's window, and the values the
  // check used and the claim stated. Every number on it comes from the API.
  chart: {
    heading: "The data over time",
    summary: (place: string, first: string, last: string, unit: string) =>
      `${place}, ${first} to ${last}, in ${unit}.`,
    window: (start: string, end: string) =>
      `The shaded band is the claim's window, ${start} to ${end}.`,
    asRead:
      "These are the values as the check read them: yearly figures made from months, or the data published by the claim's date, as the receipt says.",
    noUnit: "the series' own unit",
    chartLabel: "Data chart",
    keys: "Use the left and right arrow keys to move between values. Home and End go to the first and the last.",
    point: (period: string, value: string) => `${period}: ${value}.`,
    notes: {
      windowStart: "Start of the claim's window.",
      windowEnd: "End of the claim's window.",
      inWindow: "In the claim's window.",
      used: "The check used this value.",
      fit: (value: string) => `The fitted trend is at ${value}.`,
      claimed: (value: string, gap: string | null, holds: boolean) =>
        `The claim says ${value}${gap ? ` (allowed gap ${gap})` : ""}, which ${holds ? "holds" : "does not hold"}.`,
    },
    legend: {
      line: "The data",
      window: "The claim's window",
      used: "A value the check used",
      claimed: "A value the claim states, with its allowed gap",
      fit: "The fitted trend",
    },
    showTable: "Show as table",
    hideTable: "Hide table",
    tableLabel: "Data table",
    tableCaption: (unit: string) => `Every value, in ${unit}.`,
    columns: { period: "Period", value: "Value", notes: "Notes" },
  },
  // The distortion checks (P3.4): the claim read in other fair ways, each passed or flagged.
  // Each line comes from the API, written by code with the numbers it computed.
  framing: {
    heading: "Framing checks",
    intro:
      "HoldsUp also redid the claim in other fair ways. A flagged check does not make the number wrong, but it changes how the claim should be read.",
    kinds: {
      endpoints: "Start and end",
      per_capita: "Per person",
      real: "After inflation",
      points: "Percent or points",
      definition: "What is measured",
      stale: "How recent the figures are",
    },
    passed: "No problem found",
    flagged: "Framing matters",
  },
  // The cherry-pick heatmap: the claim's direction over other start and end years (P3.2).
  windows: {
    heading: "Other time windows",
    // How a window's result is said; `none` is for a claim without a direction.
    shows: {
      up: "The rise shows",
      down: "The fall shows",
      flat: "It stays flat",
      none: "The claim holds",
    },
    showsNot: {
      up: "The rise does not show",
      down: "The fall does not show",
      flat: "It does not stay flat",
      none: "The claim does not hold",
    },
    summary: (
      shows: string,
      held: number,
      counted: number,
      pct: number,
      need: number | null,
    ) =>
      `${shows} in ${
        held === counted ? `all ${counted}` : `${held} of the ${counted}`
      } nearby time windows${held === counted ? "" : ` (${pct}%)`}.${
        need === null ? "" : ` To hold up, a claim needs at least ${need}%.`
      }`,
    noShare:
      "The claim covers too short a span for other windows to count towards the verdict. The chart shows them for context.",
    howToRead:
      "Each square is a time window: it starts in the year of its row and ends in the year of its column. The claim's own window has a thick outline, and the dashed box holds the nearby windows that count towards the verdict.",
    subYear: (start: string, end: string) =>
      `Each window starts and ends at the same point in the year as the claim's own, ${start} to ${end}.`,
    start: "Start ↓",
    end: "End →",
    chartLabel: "Time windows chart",
    keys: "Use the arrow keys to move between windows. Home and End go to the first and last end year.",
    cell: (start: string, end: string, figure: string, verdict: string) =>
      `From ${start} to ${end}: ${figure}. ${verdict}.`,
    notAWindow: (start: string, end: string) =>
      `From ${start} to ${end}: not a time window, because the end is not after the start.`,
    noFigure: (start: string, end: string) =>
      `From ${start} to ${end}: the data gives no figure for this window.`,
    // The years the trend turns in (change points, P3.3), marked on the chart's axes.
    turns: (years: string) => `The trend turns in ${years}.`,
    ownWindow: "This is the claim's own window.",
    nearWindow: "A nearby window, so it counts towards the verdict.",
    points: (n: string) => `${n} points`,
    perYear: (n: string) => `${n}% a year`,
    units: {
      ratio: "multiples of the start value (×)",
      percent: "per cent change",
      points: "percentage points",
      cagr: "per cent a year",
      none: "the series' own unit",
    },
    legend: {
      turns: "Where the trend turns",
      empty: "No figure",
      own: "The claim's window",
      near: "Nearby windows, which count",
    },
    showTable: "Show as table",
    hideTable: "Hide table",
    tableLabel: "Time windows table",
    tableCaption: (unit: string) =>
      `Rows are start years and columns are end years. Figures are in ${unit}.`,
    holdsWord: "holds",
    failsWord: "does not hold",
    // The table's marks; the words above are what a screen reader hears.
    marks: { holds: "✓", fails: "✗", empty: "—" },
    tableKey: (shows: string, showsNot: string) => `✓ ${shows}. ✗ ${showsNot}.`,
    ownWord: "the claim's window",
  },
  cantCheck: {
    heading: "What you can do",
    cause: {
      no_series: "HoldsUp has no statistic that fits what this claim measures.",
      no_figures: (name: string) =>
        `HoldsUp has ${name}, but its source has no figures for the place or the years in this claim.`,
      unsupported: (name: string) =>
        `HoldsUp found ${name}, but it cannot recompute this kind of claim yet.`,
      unknown: "HoldsUp could not check this claim.",
    },
    tipsHeading: "Try saying it differently",
    tips: [
      "Say what is measured in everyday words, such as “unemployment rate” or “public debt as a share of GDP”.",
      "Name the place and the years.",
      "Put one figure in each sentence.",
    ],
    coverage: (name: string) => `See which places and years ${name} covers`,
    cannotLink: "What HoldsUp cannot check",
    rewordLabel: "Reword the claim",
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
    filtersHeading: "Find a statistic",
    search: "Search",
    searchPlaceholder: "A word or two, such as rent or unemployment",
    topic: "Topic",
    allTopics: "All topics",
    place: "Place",
    anyPlace: "Anywhere",
    placeGroups: "Groups",
    placeCountries: "Countries",
    placeNote:
      "Statistics that cover every country also match a country that is not in this list.",
    yearsLegend: "Years the statistic covers",
    fromYear: "From year",
    toYear: "To year",
    yearHint: "Four digits, such as 2015",
    yearsBackwards: "The first year comes after the last year.",
    shown: (shown: number, total: number) =>
      shown === total
        ? `${total} statistics`
        : `${shown} of ${total} statistics`,
    clear: "Clear filters",
    none: "No statistic matches these filters.",
    noneHint:
      "Try fewer words, another topic or a wider range of years. A claim about a statistic that is not on this list cannot be checked yet.",
    source: "Source",
    unitLabel: "Measured in",
    yearsLabel: "Years",
    coverageLabel: "Covers",
    coverage: {
      everyCountry: "every country",
      countries: (n: number) => (n === 1 ? "1 country" : `${n} countries`),
      // How a place that is not a country is named in "Covers ...".
      group: {
        EU: "the EU as a whole",
        EA: "the euro area as a whole",
        WORLD: "the world as a whole",
      } as Record<string, string>,
    },
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
  progress: {
    heading: "Progress",
    stages: {
      find: "Finding the series",
      fetch: "Fetching the data",
      recompute: "Recomputing",
      explain: "Writing the explanation",
      done: "Done",
    },
    state: {
      pending: "waiting",
      running: "in progress",
      done: "done",
      stopped: "stopped",
      skipped: "not needed",
    },
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
  // One-click re-checks with another statistic (P3.7).
  recheck: {
    heading: "Check with another statistic",
    intro:
      "The claim could also be about one of these. A re-check uses the claim as it was read here, with the statistic you pick, and gets its own link.",
    action: "Re-check",
    actionLabel: (name: string) => `Re-check with ${name}`,
    sending: "Starting…",
    of: (replaced: string | null) =>
      replaced
        ? `This is a re-check with another statistic, instead of ${replaced}.`
        : "This is a re-check with another statistic.",
    back: "See the first check",
  },
  // The /status page: the router's providers right now (P3.7).
  status: {
    meta: {
      title: "Status",
      description:
        "The language models behind HoldsUp's checks right now: which can take a request, and how many requests each has left today.",
    },
    heading: "Status",
    intro:
      "Language models read the claims, choose the statistic, plan the calculation and write the explanation; code does everything else. HoldsUp spreads that work across free providers and moves to the next one when one is busy. This is how each stands right now.",
    loading: "Asking the API…",
    down: "The HoldsUp API is not answering, so no check can run right now. Please try again in a few minutes.",
    asOf: (moment: string) => `As of ${moment}.`,
    refresh: "Refresh",
    summary: (ready: number, total: number) =>
      ready === total
        ? `All ${total} providers are ready.`
        : ready === 0
          ? "No provider is ready: new checks wait until one is."
          : `${ready} of ${total} providers are ready; checks use those.`,
    caption:
      "Each provider, the steps it serves in order of preference, and its state now.",
    columns: {
      model: "Model",
      steps: "Steps",
      state: "State",
      left: "Requests left today",
    },
    states: {
      ready: () => "Ready",
      cooling_down: (wait: string) => `Cooling down, ready in ${wait}`,
      failing: (wait: string) => `Failing, tried again in ${wait}`,
      out_of_budget: (wait: string) =>
        `Out of today's requests, back in ${wait}`,
      not_configured: () => "Not set up on this server",
    },
    noLimit: "No daily limit",
    left: (left: number, cap: number) => `${left} of ${cap}`,
    capNote:
      "Each cap is 90% of the provider's published daily limit, so HoldsUp stops before the provider says no.",
    wait: {
      seconds: (n: number) => `about ${n} second${n === 1 ? "" : "s"}`,
      minutes: (n: number) => `about ${n} minute${n === 1 ? "" : "s"}`,
      hours: (n: number) => `about ${n} hour${n === 1 ? "" : "s"}`,
    },
  },
  share: {
    heading: "Share this check",
    copyLink: "Copy link",
    copySummary: "Copy summary",
    image: "Download image",
    imageName: (id: string) => `holdsup-${id}.png`,
    native: "Share",
    linkCopied: "Link copied.",
    summaryCopied: "Summary copied.",
    failed:
      "Could not copy. You can copy the address from your browser's address bar instead.",
    // The text that is copied or shared: the claim, how it came out, and where.
    one: (claim: string, verdict: string, source: string | null) =>
      `“${claim}”\n${verdict}. Checked with HoldsUp${source ? `, against ${source}` : ""}.`,
    many: (count: number, summary: string) =>
      `HoldsUp checked ${count} claims: ${summary}.`,
    item: (n: number, claim: string, verdict: string) =>
      `${n}. “${claim}” — ${verdict}`,
  },
  report: {
    open: "Report a wrong match",
    heading: "What looks wrong?",
    kinds: {
      wrong_series: "It is checked against the wrong statistic",
      wrong_reading: "The claim was read wrongly (place, period or figure)",
      other: "Something else",
    },
    noteLabel: "Add a note (optional)",
    anonymous: "Reports are anonymous. Please do not include personal details.",
    send: "Send report",
    sending: "Sending…",
    cancel: "Cancel",
    thanks: "Thank you. Your report was recorded.",
    maxNote: 500,
  },
  // The picture a chat or social app shows for a shared check.
  og: {
    alt: "A claim, how it came out, and the figure it was checked against",
    claimed: "Claimed",
    official: "Official",
    source: (name: string) => `Checked against ${name}`,
  },
  recent: {
    heading: "Recent checks",
    intro:
      "Checks that have been picked to show how HoldsUp works. Open one to see its receipt.",
    filtersHeading: "Filter the checks",
    verdict: "Verdict",
    allVerdicts: "All verdicts",
    topic: "Topic",
    allTopics: "All topics",
    place: "Place",
    anyPlace: "Anywhere",
    shown: (shown: number, matching: number, total: number) =>
      matching === total
        ? `Showing ${shown} of ${total} checks`
        : `Showing ${shown} of ${matching} matching checks (${total} in all)`,
    showMore: "Show more checks",
    clear: "Clear filters",
    none: "No check matches these filters.",
    noneHint: "Try another verdict, topic or place, or clear the filters.",
    empty:
      "There are no checks to show yet. Paste a claim on the home page to make the first.",
    unavailable:
      "The checks could not be loaded just now. Please try again in a few minutes.",
    seeAll: "See all recent checks",
    meta: {
      description:
        "Checks of numeric claims against official statistics, each with its receipt.",
    },
  },
  about: {
    heading: "About HoldsUp",
    intro:
      "HoldsUp checks numbers. Paste a sentence with a number in it, and it finds the official statistic the number is about, recomputes the claim from that statistic's own data, and gives a verdict with a receipt you can follow.",
    what: {
      heading: "What it is",
      body: [
        "Every number has a denominator: a place, a period, a population it is measured against. A claim can leave one out, or start at a convenient year. HoldsUp puts the number back next to the data it came from.",
        "It is not a search engine and it does not weigh opinions. It compares a figure with an official statistic, using plain code for the arithmetic, and shows its working. A verdict is about the number, never about the person who said it.",
      ],
      method: "How a verdict is reached",
    },
    who: {
      heading: "Who it is for",
      items: [
        "Journalists and fact-checkers who want to check a figure before they print it.",
        "Teachers and students who want to see how a claim stands up against the data.",
        "Writers who quote numbers, and readers who wonder about them.",
        "Anyone who wants a link that settles an argument: every check has its own page.",
      ],
    },
    data: {
      heading: "Where the figures come from",
      body: "All figures come from official statistical agencies and public data projects. HoldsUp does not publish statistics of its own. Each receipt names the source and its code for the series, links to it, and says when HoldsUp fetched it.",
      statistics: (n: number) => (n === 1 ? "1 statistic" : `${n} statistics`),
      sources: [
        {
          name: "Eurostat",
          url: "https://ec.europa.eu/eurostat",
          body: "The statistical office of the European Union, covering the EU and the EFTA countries.",
        },
        {
          name: "World Bank",
          url: "https://data.worldbank.org",
          body: "Development indicators for countries around the world.",
        },
        {
          name: "Our World in Data",
          url: "https://ourworldindata.org",
          body: "Curated long-run series on emissions, energy, health and poverty.",
        },
      ],
      all: "See every statistic HoldsUp can check",
    },
    open: {
      heading: "Open source",
      body: "The code and the catalog of statistics are open under the MIT license, so anyone can read how a check works, repeat it, or improve it.",
      repo: "View HoldsUp on GitHub",
    },
    contribute: {
      heading: "Add a statistic",
      intro:
        "The catalog is a folder of small text files, one for each statistic. Adding one is a change to that folder.",
      steps: [
        {
          title: "Find the series.",
          body: "It has to come from Eurostat, the World Bank or Our World in Data. Note its code at the source.",
        },
        {
          title: "Describe it in a new file.",
          body: "Name it, give three to five phrases people really use for it, one sentence saying exactly what it measures (age range and unit included), its unit, how often it is published, the places and years it covers, and the code from the first step.",
          code: "packages/catalog/indicators/<id>.yaml",
        },
        {
          title: "Check it.",
          body: "This reads every file and rejects one that is incomplete or inconsistent. It needs no database.",
          code: "make catalog-check",
        },
        {
          title: "Raise the catalog version and propose the change.",
          body: "Every receipt records the catalog version, so changes to the catalog raise it.",
          code: "packages/catalog/VERSION",
        },
      ],
      newSource:
        "A source that is not on the list needs a small adapter that fetches its series and turns them into rows of place, period and value. Open an issue on GitHub that names the source and the series you have in mind, before writing one.",
      mistakes:
        "Found a statistic that was matched wrongly, or a figure that looks off? Use “Report a wrong match” on the claim's receipt, or open an issue.",
    },
    meta: {
      title: "About",
      description:
        "What HoldsUp is, who it is for, where its figures come from, and how to add a statistic to its open catalog.",
    },
  },
  methodology: {
    heading: "How HoldsUp judges a claim",
    intro:
      "HoldsUp compares a number in a sentence with the official statistic it is about. This page says how it decides, and where it can be wrong.",
    glanceLabel: "In short",
    glance: [
      {
        title: "Language models only read.",
        body: "They find the claim and choose the statistic. They never produce a number you see.",
      },
      {
        title: "Code does the arithmetic.",
        body: "Plain code recomputes the figure from the official data, and fixed rules set the verdict.",
      },
      {
        title: "Every check keeps a receipt.",
        body: "The source, each calculation and the gap allowed, so that anyone can repeat it.",
      },
      {
        title: "No confident match, no verdict.",
        body: "The answer is “Can't check”, never a guess.",
      },
    ],
    onThisPage: "On this page",
    // In page order: what you get, what it cannot do, then the working shown in full.
    sections: {
      verdicts: "The five verdicts",
      cannot: "What HoldsUp cannot check",
      limits: "Known limitations",
      steps: "From a sentence to a verdict",
      ops: "The calculations",
      match: "What counts as a match",
      verify: "Check our work",
    },
    by: {
      code: "Code",
      model: "Language model",
      both: "Code and a language model",
    },
    stepsIntro:
      "Every check runs these steps in order. The tag says who does the work.",
    steps: [
      {
        title: "It looks for an earlier check",
        by: "code",
        body: "If the same claim was checked before, and neither the catalog nor the allowed gaps have changed, the stored check is shown again.",
      },
      {
        title: "It reads the claims",
        by: "model",
        body: "A language model finds each claim and writes it in a fixed form: the statistic, the place, the period, and what is asserted (a figure, a direction or a rank). The pasted text is only read. Nothing in it can make HoldsUp do anything.",
      },
      {
        title: "It finds the official statistic",
        by: "both",
        body: "The catalog is searched for the closest statistics. Those with no data for the claim's place are dropped, and a language model chooses one of the rest, or none. With no confident choice the answer is “Can't check”.",
      },
      {
        title: "It fetches the data",
        by: "code",
        body: "The series comes from the source's own service: Eurostat, the World Bank or Our World in Data. The receipt keeps a fingerprint of the data, so a later change can be seen.",
      },
      {
        title: "It plans the calculation",
        by: "model",
        body: "A language model chooses calculations from the fixed list below and says what to run them on. It writes no numbers, and code checks the plan first.",
      },
      {
        title: "It runs the calculation",
        by: "code",
        body: "Plain code does the arithmetic and records each calculation with its inputs and result. That record is the receipt.",
      },
      {
        title: "It decides the verdict",
        by: "code",
        body: "Fixed rules compare each computed figure with the claimed one, within the allowed gaps. No model is involved.",
      },
      {
        title: "It explains",
        by: "model",
        body: "A language model writes two or three sentences from the computed results only. If they contain a number that is not among the results, they are thrown away and code writes a plainer explanation.",
      },
    ],
    opsIntro:
      "A model can only choose from these eight. Each is a plain function with its own tests.",
    ops: [
      {
        name: "Value at a date",
        body: "The official figure for one place and period. If that period has no value, the nearest one within a set distance is used, and the receipt says so.",
      },
      {
        name: "Change between two periods",
        body: "As an amount, as a percentage, in percentage points, or as a multiple (“halved”, “doubled”).",
      },
      {
        name: "Average yearly growth",
        body: "The steady yearly rate that would take the start value to the end value.",
      },
      {
        name: "Trend",
        body: "The slope of a straight line through the period, and how much of the movement that line explains.",
      },
      {
        name: "Comparison of two places",
        body: "The difference and the ratio between them for one period.",
      },
      {
        name: "Position in a list",
        body: "Where a place stands among the others for one period.",
      },
      {
        name: "Per person",
        body: "A series divided by the population, so that places of different sizes can be compared.",
      },
      {
        name: "Adjusted for inflation",
        body: "A series divided by a price index, to the prices of one base year.",
      },
    ],
    gaps: {
      intro: (version: number) =>
        `A claim holds when the official figure is within an allowed gap of the figure claimed. The gap depends on the kind of figure. The numbers below are the ones the checks use now (version ${version}), and each receipt lists the gap used for each of its figures.`,
      kindsHeading: "By kind of figure",
      kinds: {
        level: {
          label: "A level",
          example: "“debt of 2.9 trillion euros”",
        },
        level_rate: {
          label: "A rate or share, stated as a level",
          example: "“youth unemployment is 20%”",
        },
        absolute: {
          label: "A change in an amount",
          example: "“grew by 116 billion euros”",
        },
        percent: {
          label: "A percentage change",
          example: "“down 23%”, also a growth rate",
        },
        percentage_points: {
          label: "A change in percentage points",
          example: "“fallen 12 points”",
        },
        ratio: {
          label: "A multiple",
          example: "“halved”, “doubled”",
        },
        rank: {
          label: "A position",
          example: "“the lowest in the EU”",
        },
      },
      // The unit a fixed gap is written in, where the figure's own unit would be unclear.
      units: { percentage_points: "points" } as Record<string, string>,
      // "the largest of A, B and C", then what is added on top.
      largest: (list: string) => `The largest of ${list}.`,
      relative: (share: string) => `${share} of the claimed figure`,
      absolute: (n: number, unit: string) =>
        unit ? `${n} ${unit}` : `${n} in the figure's own unit`,
      rounding: "half a unit of the last digit written (“2.3” allows 0.05)",
      plus: (share: string) =>
        `Then ${share} of the claimed figure is added, to allow for data revised since the claim was made.`,
      exact: "No gap: the position has to be exactly right.",
      othersHeading: "Other rules",
      flat: (share: string) =>
        `“Flat” or “stable” holds when the end value is within ${share} of the start value.`,
      trend: (share: string) =>
        `“Rising” or “falling” also needs the straight line to explain at least ${share} of the ups and downs.`,
      // Change points: `share` is how much of the change a start or end may carry.
      turns: (share: string) =>
        `A claim that starts or ends at a peak, a trough or where the trend turns is flagged when that year carries it: from the usual level around then, the change would go the other way or be more than ${share} smaller. Then the framing matters.`,
      // The stale-data check: a claim about the present on figures `years` or more years old.
      stale: (years: number) =>
        `A claim about the present is flagged when its latest figure is for a period that ended ${years === 1 ? "1 year" : `${years} years`} or more before the claim was made (or before today, if it has no date).`,
      // The cherry-pick sweep: `reach` and `minYears` in years, `share` the framing threshold.
      windows: (reach: number, minYears: number, share: string) =>
        `A claim that something rose, fell or stayed flat over at least ${minYears === 1 ? "1 year" : `${minYears} years`} is also redone with its start moved up to ${reach === 1 ? "1 year" : `${reach} years`} either way and its end up to ${reach === 1 ? "1 year" : `${reach} years`} earlier. To hold up, it has to go the same way in at least ${share} of those time windows; otherwise the framing matters.`,
      periodGap: (parts: string) =>
        `When the period named has no value, the nearest one is used if it is close enough, and the receipt says so. “Close enough” is ${parts}. Farther away, the claim can't be checked.`,
      periodUnit: {
        annual: (n: number) => (n === 1 ? "1 year" : `${n} years`),
        semiannual: (n: number) =>
          n === 1 ? "1 half-year" : `${n} half-years`,
        quarterly: (n: number) => (n === 1 ? "1 quarter" : `${n} quarters`),
        monthly: (n: number) => (n === 1 ? "1 month" : `${n} months`),
      } as Record<string, (n: number) => string>,
      periodFor: (unit: string, kind: string) => `${unit} for ${kind} series`,
      periodKind: {
        annual: "yearly",
        semiannual: "half-yearly",
        quarterly: "quarterly",
        monthly: "monthly",
      } as Record<string, string>,
      unavailable:
        "The allowed gaps could not be loaded just now. Each receipt lists the gap used for each figure.",
    },
    verdictsIntro:
      "Each verdict is set by a rule, never by a person's judgement of the claim.",
    cannotIntro: "In these cases the answer is “Can't check”, with the reason.",
    cannot: [
      "Claims about records, targets or streaks: “the highest ever”, “met its target”, “for ten years in a row”.",
      "Claims that give neither a figure nor a direction, such as “things are getting worse”.",
      "Anything that is not about a number: opinions, quotes and events.",
      "Survey and poll results.",
      "A place or a period that the source has no data for.",
    ],
    cannotCatalog: {
      before: "Statistics that are not in the catalog. ",
      link: "See what can be checked",
      after: ".",
    },
    limits: [
      {
        title: "The statistic may be close, not identical.",
        body: "Statistics differ in age range, definition, unit or place. The receipt names the series that was used and its definition, so that you can see whether it is the one meant. If it is not, say so with “Report a wrong match” on that claim.",
      },
      {
        title: "Language models can misread a sentence.",
        body: "Reading the claim and choosing the statistic are done by language models, and they can be wrong. Everything after that is code, and the receipt shows how the claim was read.",
      },
      {
        title: "Data gets revised.",
        body: "A check uses the data as it was when the check ran, with its date and fingerprint. A claim made years ago may have been right for the figures of its day.",
      },
      {
        title: "A true figure can still mislead.",
        body: "A claim can be right for the years it names and still give a wrong picture, for example by starting at a peak. For a claim that something rose, fell or stayed flat, HoldsUp redoes the calculation with the start and end moved by a few years, and says the framing matters when the claim goes the same way in too few of them. It does not yet look at per-person or inflation-adjusted views.",
      },
      {
        title: "A verdict is about the number.",
        body: "It says what the data shows. It is not a judgement of the person who said it.",
      },
    ],
    verify: {
      body: "The code and the catalog are open. Each receipt links to the source and lists every calculation, so that anyone can repeat it.",
      link: "Read the code on GitHub",
    },
    meta: {
      title: "Methodology",
      description:
        "How HoldsUp reads a claim, finds the official statistic, recomputes it with code, and decides a verdict.",
    },
  },
  legend: {
    heading: "What the verdicts mean",
    onThisPage: "On this page",
    // The framing threshold comes with each result; without one the rule is said without a number.
    // `windows` is whether this page's verdicts compared other time windows at all.
    holds: (pct: number | null, windows: boolean) =>
      windows
        ? `Every figure in the claim is within the allowed gap of the official figure, and a claim about a change over several years holds ${
            pct === null
              ? "across most comparable time windows"
              : `in at least ${pct}% of comparable time windows`
          }.`
        : "Every figure in the claim is within the allowed gap of the official figure. Other time windows are not compared yet.",
    framing: (pct: number | null, windows: boolean) =>
      windows
        ? `The figures are within the allowed gap, but the claim holds in ${
            pct === null ? "too few" : `fewer than ${pct}% of`
          } comparable time windows, or fails a check for misleading framing.`
        : "The figures are within the allowed gap, but the claim fails a check for misleading framing.",
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
      notebook: "Or run the notebook.",
      notebookBody:
        "It repeats every calculation of this check in Python, from the values each one read, and stops if a number differs from this receipt. It needs only Python 3.10 or later.",
      notebookLink: "Download the notebook (.ipynb)",
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
