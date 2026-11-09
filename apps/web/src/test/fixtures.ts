import type {
  CatalogEntry,
  CheckResult,
  CheckView,
  ClaimResult,
} from "@/lib/api/client";

/**
 * Complete, typed results for tests, shaped like what the API stores. A schema change
 * that breaks them fails type checking instead of passing silently.
 */

export const versions: CheckResult["versions"] = {
  app: "0.1.0",
  catalog: "0.4.0",
  tolerances: 2,
};

const indicator: NonNullable<ClaimResult["indicator"]> = {
  id: "unemployment_rate_monthly",
  name: "Unemployment rate (monthly)",
  source: "eurostat",
  source_code: "une_rt_m",
  unit: "% of labour force",
  frequency: "monthly",
  definition:
    "Unemployed people as a percentage of the labour force, monthly, seasonally adjusted (ILO definition).",
};

const data: NonNullable<ClaimResult["data"]> = {
  source: "eurostat",
  dataset: "une_rt_m",
  url: "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m?format=JSON&geo=IT",
  retrieved_at: "2026-11-07T16:45:30Z",
  raw_sha256: "4f556131ab70",
  label: "Unemployment by sex and age - monthly data",
  updated: "2026-11-05T23:00:00+0100",
  citation: "Eurostat (une_rt_m)",
  places: ["IT"],
  rows: 525,
};

const model = {
  step: "explain",
  provider: "groq",
  model: "gpt-oss-20b",
  label: "GPT-OSS 20B (Groq)",
} as const;

/** "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.": it holds. */
export const holdingClaim: ClaimResult = {
  index: 0,
  claim: {
    quote: "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
    indicator_phrase: "unemployment rate",
    geo: "IT",
    geo_basis: "stated",
    peers: [],
    start: "2015",
    start_basis: "stated",
    end: "2023",
    end_basis: "stated",
    assertion: {
      type: "percentage_points",
      value: null,
      direction: "down",
      unit: "%",
      start_value: 11.9,
      end_value: 7.7,
      operator: "about",
    },
    speaker: null,
    said_on: null,
    notes: [],
  },
  indicator,
  alternatives: [],
  suggestions: [],
  match_reason: "Matches the exact definition: the monthly unemployment rate.",
  data,
  extra_sources: [],
  plan_reason: "Compare the yearly average rate in 2015 with 2023.",
  operations: [
    {
      op: "change",
      args: {
        geo: "IT",
        start: "2015",
        end: "2023",
        kind: "percentage_points",
      },
      inputs: [
        { geo: "IT", period: "2015", value: 12.02 },
        { geo: "IT", period: "2023", value: 7.68 },
      ],
      value: -4.34,
      extras: {},
      series: null,
      unit: "percentage points",
      flags: [
        {
          code: "annual_value",
          detail: "A year's value is the average of its 12 monthly values.",
          requested: null,
          used: null,
          distance: null,
          items: [],
        },
      ],
    },
  ],
  answer: [0],
  verdict: {
    label: "supported",
    reason: "Holds within tolerance.",
    parts: [
      {
        name: "assertion",
        holds: true,
        computed: -4.34,
        detail: "change -4.34; claim says down",
        operator: "about",
      },
      {
        name: "start value",
        holds: true,
        computed: 12.02,
        asserted: 11.9,
        tolerance: 0.169,
        period: "2015",
        operator: "about",
        detail: "computed 12.02 for 2015, asserted 11.9 ± 0.169",
      },
      {
        name: "end value",
        holds: true,
        computed: 7.68,
        asserted: 7.7,
        tolerance: 0.127,
        period: "2023",
        operator: "about",
        detail: "computed 7.68 for 2023, asserted 7.7 ± 0.127",
      },
    ],
    window_share: 0.9,
    framing_threshold: 0.7,
    distortions: [],
    tolerances_version: 2,
  },
  explanation:
    "Italy's unemployment rate went from 12.02% in 2015 to 7.68% in 2023, a fall of 4.34 points.",
  explanation_source: "model",
  models: [model],
  notes: [],
  retryable: false,
};

/** Renzi, 2018: the end value holds, the 12-point fall and the start value do not. */
export const partlyClaim: ClaimResult = {
  ...holdingClaim,
  index: 0,
  claim: {
    quote: "youth unemployment has fallen 12 points, from 44% to 32%.",
    indicator_phrase: "youth unemployment rate",
    geo: "IT",
    geo_basis: "inferred",
    peers: [],
    start: "2014-02",
    start_basis: "office",
    end: "latest",
    end_basis: "stated",
    assertion: {
      type: "percentage_points",
      value: 12,
      direction: "down",
      unit: "points",
      start_value: 44,
      end_value: 32,
      operator: "about",
    },
    speaker: "Renzi",
    said_on: "2018",
    notes: [],
  },
  operations: [
    {
      op: "change",
      args: {
        geo: "IT",
        start: "2014-02",
        end: "latest",
        kind: "percentage_points",
      },
      inputs: [
        { geo: "IT", period: "2014-02", value: 42.7 },
        { geo: "IT", period: "2018-11", value: 32 },
      ],
      value: -10.7,
      extras: {},
      series: null,
      unit: "percentage points",
      flags: [
        {
          code: "as_of",
          detail:
            "claim date 2018: latest is the last period published by then, 2018-11",
          requested: "latest",
          used: "2018-11",
          distance: null,
          items: [],
        },
      ],
    },
  ],
  verdict: {
    label: "partly_supported",
    reason: "Holds for end value; not for assertion, start value.",
    parts: [
      {
        name: "assertion",
        holds: false,
        computed: -10.7,
        asserted: -12,
        tolerance: 0.5,
        operator: "about",
        detail: "computed -10.7, asserted -12 ± 0.5",
      },
      {
        name: "start value",
        holds: false,
        computed: 42.7,
        asserted: 44,
        tolerance: 0.94,
        period: "2014-02",
        operator: "about",
        detail: "computed 42.7 for 2014-02, asserted 44 ± 0.94",
      },
      {
        name: "end value",
        holds: true,
        computed: 32,
        asserted: 32,
        tolerance: 0.82,
        period: "2018-11",
        operator: "about",
        detail: "computed 32 for 2018-11, asserted 32 ± 0.82",
      },
    ],
    window_share: null,
    framing_threshold: 0.7,
    distortions: [],
    tolerances_version: 2,
  },
  explanation:
    "Youth unemployment in Italy was 42.7% in February 2014, not the 44% claimed. It fell to 32% in November 2018.",
};

/** A claim HoldsUp could not match to any official statistic. */
export const unmatchedClaim: ClaimResult = {
  index: 0,
  claim: { ...holdingClaim.claim, quote: "Italy has 20 million people." },
  indicator: null,
  data: null,
  alternatives: [],
  suggestions: [{ id: "population", name: "Total population (Eurostat)" }],
  match_reason: "",
  extra_sources: [],
  operations: [],
  answer: [],
  verdict: {
    label: "cant_check",
    reason: "No official statistic matches this claim.",
    parts: [],
    distortions: [],
  },
  explanation: "",
  explanation_source: "template",
  models: [],
  notes: [],
  retryable: false,
};

export function checkResult(
  claims: ClaimResult[],
  over: Partial<CheckResult> = {},
): CheckResult {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    text: claims.map((c) => c.claim.quote).join(" "),
    created_at: "2026-11-07T10:00:00Z",
    finished_at: "2026-11-07T10:00:06Z",
    cached_from: null,
    claims,
    versions,
    models: [],
    notes: [],
    ...over,
  };
}

export function checkView(
  over: Partial<CheckView> & Pick<CheckView, "status">,
): CheckView {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    text: holdingClaim.claim.quote,
    created_at: "2026-11-07T10:00:00Z",
    finished_at: null,
    result: null,
    error: null,
    ...over,
  };
}

/** One catalog entry as the API lists it; a test overrides only what it is about. */
export function catalogEntry(
  over: Partial<CatalogEntry> & Pick<CatalogEntry, "id">,
): CatalogEntry {
  return {
    name: over.id,
    theme: "economy",
    definition: "What it measures.",
    unit: "%",
    source: "Eurostat",
    frequency: "annual",
    first_year: 2000,
    last_year: null,
    source_code: "abc_123",
    aliases: [],
    countries: ["DE", "FR", "IT"],
    groups: ["EU"],
    all_countries: false,
    ...over,
  };
}
