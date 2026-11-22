// Text for pages that render only on the server: about, methodology, privacy and terms,
// and the home page's video section.
// It is kept apart from `strings` so the browser never downloads it; no client module may
// import this file (src/lib/__tests__/strings-boundaries.test.ts checks).
export const pageStrings = {
  tour: {
    // The hero's link down to the video in "How it works".
    watch: "Watch the one-minute tour",
    caption:
      "A one-minute tour of a real check. The words are on screen, so it works with the sound off.",
    label: "HoldsUp in one minute",
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
        "Found a statistic that was matched wrongly, or a figure that looks off? Use “Report a problem” on the claim's receipt, or open an issue.",
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
        body: "Statistics differ in age range, definition, unit or place. The receipt names the series that was used and its definition, so that you can see whether it is the one meant. If it is not, say so with “Report a problem” on that claim.",
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
  // Privacy and terms in one page (/privacy), linked from the footer and the check form.
  // Every statement here must stay true of the code: what is stored (db/models.py), who gets
  // the text (router/providers.yaml), what the browser keeps (lib/history.ts, lib/theme.ts).
  privacy: {
    heading: "Privacy and terms",
    intro:
      "HoldsUp is a free, open-source project with no accounts, no ads and no tracking. This page says what happens to the text you send, who else handles it, how to have a check removed, and the few rules for using the site.",
    updated: {
      label: "Last updated",
      iso: "2026-11-22",
      text: "22 November 2026",
    },
    glanceLabel: "At a glance",
    onThisPage: "On this page",
    glance: [
      {
        title: "No cookies, no tracking",
        body: "No account, no analytics, no ads. Nothing follows you to other sites.",
      },
      {
        title: "Your check is saved",
        body: "The text and its result are kept, and anyone with the link can open them.",
      },
      {
        title: "Language models read it",
        body: "Your text is sent to a model provider to find its claims and plan the check.",
      },
      {
        title: "You can have it removed",
        body: "Ask from the check's own page, privately, with no account.",
      },
    ],
    kept: {
      heading: "What HoldsUp keeps",
      items: [
        "The text you submit and its result: the claims found, the statistics they were matched to, the figures, the verdicts and the receipt. If you submit a link, HoldsUp's server reads that page and keeps its text in the same way.",
        "Each check gets an address that cannot be guessed, and it is kept with no end date so that shared links keep working. Anyone who has the link can open it, and it can be shown on other sites with the embed code.",
        "Checks are not listed anywhere and are hidden from search engines. The examples on the home page and under Recent checks are ones the project ran itself.",
        "A later check of exactly the same text can reuse a stored result instead of asking the models again. When a source revises its figures, a check can be computed again; the update gets its own link.",
        "If you report a problem with a check, the report (what kind of problem, and your note if you add one) is kept with that check.",
      ],
      never:
        "HoldsUp never asks for your name or email address, and it does not build a profile of you. Please do not paste personal information about yourself or anyone else.",
    },
    who: {
      heading: "Who else handles your text",
      intro:
        "HoldsUp runs on outside services. Each one receives only what it needs and handles it under its own terms. Most of them are in the United States, so your text is processed there.",
      groups: [
        {
          title: "Language models",
          body: "Your text goes to one of these at a time, Groq first, to find the claims in it, plan each check and word the explanation. The arithmetic never comes from a model.",
          services: [
            {
              name: "Groq",
              url: "https://groq.com/privacy-policy",
              role: "First choice",
              where: "United States",
            },
            {
              name: "Cerebras",
              url: "https://www.cerebras.ai/privacy-policy",
              role: "When Groq is busy",
              where: "United States",
            },
            {
              name: "Mistral AI",
              url: "https://legal.mistral.ai/terms/privacy-policy",
              role: "Fallback",
              where: "France",
            },
            {
              name: "OpenRouter",
              url: "https://openrouter.ai/privacy",
              role: "Last resort, free models; their hosts may keep prompts",
              where: "United States",
            },
          ],
        },
        {
          title: "Hosting",
          body: "These run the site. Like any web host they keep short-lived request logs, which include your IP address.",
          services: [
            {
              name: "Vercel",
              url: "https://vercel.com/legal/privacy-notice",
              role: "Serves the website, and keeps a copy of each finished check's page so it opens fast; removing a check removes that copy too",
              where: "United States",
            },
            {
              name: "Google Cloud Run",
              url: "https://cloud.google.com/terms/cloud-privacy-notice",
              role: "Runs the checking service",
              where: "United States",
            },
            {
              name: "Neon",
              url: "https://neon.com/privacy-policy",
              role: "The database the checks are kept in",
              where: "United States",
            },
          ],
        },
      ],
      sources:
        "The statistics come from Eurostat, the World Bank and Our World in Data. HoldsUp asks them only for a series and a place, never for your text, and the request comes from its server, not from your browser.",
      voice:
        "If you use the Speak button, your browser's own speech service turns your voice into text, and may send the audio to its provider (Google for Chrome, Apple for Safari). HoldsUp receives only the text you then submit.",
    },
    address: {
      heading: "Your IP address",
      body: "To stop one address from sending too many checks or reports, HoldsUp counts requests per address in memory for an hour. It does not store addresses. Its own logs record which pages and checks were asked for, and a check's length and verdicts, but never its text or your address. The hosts above keep their own request logs for a short time.",
    },
    browser: {
      heading: "In your browser",
      body: "HoldsUp sets no cookies, so there is no cookie banner. It keeps two things in your browser's local storage: your light or dark choice, and the list of your recent checks. They stay on your device, are never sent anywhere, and are gone when you clear your browser's data. Fonts and scripts are served by HoldsUp itself, so no third party sees your visit.",
    },
    basis: {
      heading: "Why, and on what basis",
      body: "Your text is used to run the check you ask for and to keep its result at its link, and your address only to keep the service from being overloaded. Under the EU and UK GDPR the basis for both is legitimate interest (Article 6(1)(f)): providing a free, shareable check and keeping it working for everyone. HoldsUp is a personal, non-commercial project; it does not sell or share data for advertising.",
    },
    remove: {
      heading: "Removing a check, and your rights",
      steps: [
        "Open the check and choose “Report a problem” under one of its claims.",
        "Pick “It shows personal information: please remove this check”, and send. No account is needed, and the request is not public.",
        "The check is then deleted, together with every stored check of the same text.",
      ],
      noClaims:
        "If the check has no claims, or for anything else (seeing what is stored about you, correcting it, or objecting), open an issue on GitHub. Do not put the personal information or the check's link in the issue; ask for a private way to send it.",
      issue: "Open an issue on GitHub",
      authority:
        "You also have the right to complain to the data protection authority where you live.",
      controller:
        "HoldsUp is run by its maintainer, sinahatami on GitHub, who decides how this data is used.",
    },
    terms: {
      heading: "Terms of use",
      intro: "By using HoldsUp you agree to these terms.",
      items: [
        "Verdicts are made by software and can be wrong. Read the receipt before you rely on one. Nothing here is legal, financial or other professional advice.",
        "A verdict is about the number, not about the person who said it.",
        "HoldsUp is free and provided as it is, with no promise that it is available, complete or correct, as far as the law allows.",
        "Do not submit personal information about anyone, or anything unlawful, and do not try to overload or misuse the service. There are limits on how many checks one address can make in an hour.",
        "The code is open source under the MIT license. The figures belong to their sources and are used under those sources' own licenses.",
      ],
      sources: "Where the figures come from",
      license: "Read the MIT license",
    },
    changes: {
      heading: "Changes to this page",
      body: "When something here changes, the date at the top changes with it, and every earlier version is in the project's history on GitHub.",
      history: "See this page's history",
      historyUrl:
        "https://github.com/sinahatami/holdsup/commits/main/apps/web/src/lib/strings/pages.ts",
    },
    meta: {
      title: "Privacy and terms",
      description:
        "What HoldsUp keeps, who else handles your text, how to have a check removed, and the terms for using the site.",
    },
  },
} as const;
