// All interface text lives in this folder (RTL/i18n readiness). This file holds the text client
// code may use; pages.ts the text of server-only pages; boundary.ts the error pages' text.
import { boundaryStrings } from "./boundary";

export const strings = {
  locale: boundaryStrings.locale,
  dir: boundaryStrings.dir,
  appName: "HoldsUp",
  tagline: "Every number has a denominator.",
  metaDescription:
    "HoldsUp checks numeric claims against official statistics and shows its work.",
  // A wait in words: "about 15 seconds" in a sentence, "15 s" on a button that counts down.
  wait: {
    seconds: (n: number) => `about ${n} second${n === 1 ? "" : "s"}`,
    minutes: (n: number) => `about ${n} minute${n === 1 ? "" : "s"}`,
    hours: (n: number) => `about ${n} hour${n === 1 ? "" : "s"}`,
    short: {
      seconds: (n: number) => `${n} s`,
      minutes: (n: number) => `${n} min`,
      hours: (n: number) => `${n} h`,
    },
  },
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
      at_capacity: "HoldsUp is at capacity",
      unavailable: "HoldsUp could not finish this check",
      other: "This check could not be completed",
    },
    retry: "Try again",
    // The wait is short ("42 s", "12 min"): the button counts it down.
    retryIn: (wait: string) => `Try again in ${wait}`,
    // Every model provider is busy or out of today's requests (the API's at-capacity problem).
    capacity: {
      body: "Every free model provider HoldsUp uses is busy or has run out of today's requests.",
      backIn: (wait: string) => `Back in ${wait}.`,
      galleryHeading: "While you wait",
      galleryIntro:
        "These claims were checked earlier, so their receipts open now, with no model needed.",
    },
    offline: {
      heading: "You are offline",
      body: "Pages and checks that need HoldsUp will not load until your connection is back.",
    },
    reconnect: "Reconnect",
  },
  error: boundaryStrings.error,
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
    // The release the site runs, linked to that release's notes on GitHub.
    version: (v: string) => `v${v}`,
    releaseNotes: "Release notes for",
    releaseUrl: (v: string) =>
      `https://github.com/sinahatami/holdsup/releases/tag/v${v}`,
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
    // The tooltip on the remove button: the start of its name, short enough for one line.
    removeShort: "Remove from your list",
    summary: (holds: number, total: number) =>
      `${holds} of ${total} claims hold up`,
    running: "Result not seen yet",
  },
  home: {
    // The page title is the tagline, with its last word set apart.
    titleLead: "Every number has a",
    titleEnd: "denominator.",
    // A fixed example figure with its denominator. Yearly average of Eurostat une_rt_m, Italy.
    denominator: {
      aside: "a number alone says little…",
      value: "7.68%",
      caption:
        "Italy's unemployment rate as a yearly average for 2023, with the four questions every figure has to answer.",
      partsLabel: "What the figure is measured against",
      parts: [
        { question: "where?", label: "Place", value: "Italy" },
        { question: "when?", label: "Period", value: "2023" },
        { question: "of whom?", label: "Population", value: "Labour force" },
        { question: "says who?", label: "Source", value: "Eurostat" },
      ],
    },
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
      "Paste a sentence with a number in it, or a link to an article. HoldsUp finds the official series, recomputes the claim, and tells you whether it holds up.",
    inputLabel: "The claim to check",
    // One short line under the label. It says "speak" only where the Speak button is shown.
    helper: "Type a claim or paste a link to an article. English only for now.",
    helperVoice:
      "Type or speak a claim, or paste a link to an article. English only for now.",
    // Replaces the helper while the box holds nothing but a link.
    linkHelper:
      "A link: HoldsUp reads the page and checks its paragraphs with figures.",
    placeholder:
      "e.g. Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
    submit: "Check this claim",
    submitLink: "Check this page",
    submitting: "Sending…",
    reading: "Reading the page…",
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
      "Italian workers' average net pay rose 4.6% between 2021 and 2023.",
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
    // A check of an article link: the page's paragraphs with figures, and where they came from.
    pageHeading: "What HoldsUp read on the page",
    pageFrom: "From",
    pageRead: (date: string) => `read on ${date}.`,
    pageAll: "Only its paragraphs with figures were checked.",
    pageSome: (used: number, found: number) =>
      `It has ${found} paragraphs with figures. Only the first ${used === 1 ? "one was" : `${used} were`} checked: that is as much as one check holds.`,
    explanationHeading: "Why",
    loading: "Loading the check…",
    connectionLost: "Lost the connection to the live trace.",
    retryAfter: (wait: string) => `Try again in ${wait}.`,
    cached: "Answered from an earlier check of the same claim.",
    cachedLink: "See that check",
    back: boundaryStrings.back,
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
  // How sure the check is of a verdict (P4.5). When it abstains, the reason comes from the API,
  // written by code from the check's own signals.
  confidence: {
    label: {
      high: "High confidence",
      medium: "Medium confidence",
      low: "Low confidence",
    },
    help: "How likely this verdict is to be right, judged from how clearly the statistic fits the claim, how old and how long the data is, how close the figure is to the tolerance, and whether backup models did the work.",
    abstained: "Can't check confidently",
    numbersAlone: "What the numbers alone say:",
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
      "Each square is a time window: it starts in the year of its row and ends in the year of its column. The claim's own window is ringed in red, and the dashed box holds the nearby windows that count towards the verdict.",
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
  // The claim watch (S1): stored checks compared again with the sources, and computed again
  // (by code, no model) when a source revised a figure they read.
  watch: {
    revised: "A source has revised the figures behind this check.",
    checkedAgain: (date: string) => `HoldsUp checked it again on ${date}:`,
    stands: "the verdict still stands.",
    allStand: "every verdict still stands.",
    nowIs: (label: string) => `the verdict is now “${label}”.`,
    changed: (n: number, total: number) => `${n} of ${total} verdicts changed.`,
    seeUpdate: "See the updated check",
    updates: (date: string) =>
      `This updates the check of ${date}. A source revised figures it read, so HoldsUp computed the claims again with the same statistics and plans. No model was asked: the explanation is written by code.`,
    seeEarlier: "See the earlier check",
    claimWas: (n: number | null, label: string) =>
      n === null ? `It was “${label}”.` : `Claim ${n} was “${label}”.`,
    figure: (what: string, before: string, after: string) =>
      `${what}: from ${before} to ${after}`,
    framingOnly: "Only a framing check moved.",
    compared: (date: string) =>
      `Figures last compared with the sources on ${date}.`,
    embedUpdated: (date: string) => `Updated ${date} with revised figures`,
  },
  share: {
    heading: "Share this check",
    copyLink: "Copy link",
    copySummary: "Copy summary",
    image: "Download image",
    imageName: (id: string) => `holdsup-${id}.png`,
    native: "Share",
    embed: "Copy embed code",
    linkCopied: "Link copied.",
    summaryCopied: "Summary copied.",
    embedCopied: "Embed code copied. Paste it into a page's HTML.",
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
    brandAlt:
      "The HoldsUp logo, a division sign whose upper dot is a quotation mark, over the words: Every number has a denominator.",
    claimed: "Claimed",
    official: "Official",
    source: (name: string) => `Checked against ${name}`,
  },
  // A check's verdict on another site, inside an iframe (/embed/[id]). Its links open HoldsUp
  // in a new tab, so the reader keeps the page they were on.
  embed: {
    pageTitle: "Embedded check",
    // The iframe's title, which a screen reader announces before entering it.
    frameTitle: (title: string) => `HoldsUp: ${title}`,
    fullReceipt: "See the full receipt on HoldsUp",
    openCheck: "Open this check on HoldsUp",
    openHoldsUp: "Go to HoldsUp",
    running: "This check is still running.",
    failed: "This check could not finish.",
    unavailable: "HoldsUp could not load this check just now.",
    noClaims: "HoldsUp found no claim with a number in this text.",
    missing: "No check at this link.",
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
  // The head of a checked claim: the editor's notes in its margin and the claim set over its
  // denominator. Every pen note is said again in plain text in the receipt.
  claim: {
    margin: {
      figure: (when: string, official: string, holds: boolean) =>
        `${when}: ${official}. ${holds ? "Close enough." : "Too far off."}`,
      direction: (official: string, holds: boolean) =>
        `Official change: ${official}. ${holds ? "Right way." : "Wrong way."}`,
      framing: "Other years tell another story.",
    },
    denominator: {
      heading: "The claim, with its denominator",
      claimed: "Claimed",
      official: "Official",
      // What the claim left out, which HoldsUp had to fill in.
      unstatedNames: { place: "place", period: "years" },
      unstated: (names: string) =>
        `The claim does not name its ${names}. The receipt says how HoldsUp read it.`,
      stated: "As the claim states it.",
      question: (name: string) => `${name}?`,
      // Said in place of the arrow between a start and an end figure.
      to: "to",
    },
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
