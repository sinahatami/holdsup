import type { Page } from "@playwright/test";

export const CHECK_ID = "11111111-1111-4111-8111-111111111111";
const API = "http://api.test";
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "*",
};

const step = (event: string, step: string, extra: object = {}) => ({
  event,
  step,
  claim: null,
  status: event === "step_done" ? "ok" : null,
  summary: "",
  models: [],
  ms: event === "step_done" ? 12 : null,
  ...extra,
});

export const result = {
  id: CHECK_ID,
  text: "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
  created_at: "2026-11-07T10:00:00Z",
  finished_at: "2026-11-07T10:00:06Z",
  cached_from: null,
  claims: [
    {
      index: 0,
      claim: {
        quote:
          "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.",
        indicator_phrase: "unemployment rate",
        geo: "IT",
        peers: [],
        start: "2015",
        end: "2023",
        assertion: {
          type: "percentage_points",
          value: -4.2,
          direction: "down",
          unit: "pp",
        },
        notes: [],
      },
      indicator: {
        id: "eurostat-une-rt-a",
        name: "Unemployment rate, annual",
        source: "eurostat",
        source_code: "une_rt_a",
        unit: "%",
        frequency: "annual",
        definition: "Unemployed persons as a share of the labour force.",
      },
      alternatives: [],
      match_reason: "Clear match.",
      data: {
        source: "Eurostat",
        dataset: "une_rt_a",
        url: "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_a",
        retrieved_at: "2026-11-07T10:00:03Z",
        raw_sha256: "9f2c0de1",
        label: "Unemployment",
        places: ["IT"],
        rows: 9,
      },
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
            { geo: "IT", period: "2015", value: 11.9 },
            { geo: "IT", period: "2023", value: 7.7 },
          ],
          value: -4.2,
          extras: {},
          series: null,
          unit: "pp",
          flags: [],
        },
      ],
      answer: [0],
      verdict: {
        label: "supported",
        reason: "The change matches the claim within tolerance.",
        parts: [],
        distortions: [],
      },
      explanation:
        "Italy's unemployment rate went from 11.9% in 2015 to 7.7% in 2023, a fall of 4.2 points.",
      explanation_source: "model",
      models: [{ step: "explain", provider: "groq", model: "gpt-oss-20b" }],
      notes: [],
      retryable: false,
    },
  ],
  versions: { app: "0.1.0", catalog: "0.2.0", tolerances: 1 },
  models: [],
  notes: [],
};

const sse = (events: [string, object][]) =>
  events
    .map(
      ([name, data], i) =>
        `id: ${i}\nevent: ${name}\ndata: ${JSON.stringify(data)}\n\n`,
    )
    .join("");

/** Mocks the browser's calls to the API: submit, read, and the SSE stream. */
export async function mockApi(
  page: Page,
  outcome: "result" | "error" | "rate-limit" = "result",
) {
  await page.route(`${API}/**`, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (req.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers: CORS });
    if (req.method() === "POST" && url.pathname === "/v1/checks") {
      if (outcome === "rate-limit") {
        return route.fulfill({
          status: 429,
          headers: { ...CORS, "content-type": "application/problem+json" },
          body: JSON.stringify({
            type: "about:blank",
            title: "Too many checks",
            status: 429,
            detail: "You have reached the hourly limit.",
          }),
        });
      }
      return route.fulfill({
        status: 202,
        headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify({
          id: CHECK_ID,
          status: "queued",
          cached: false,
          stream_url: `/v1/checks/${CHECK_ID}/stream`,
          result_url: `/v1/checks/${CHECK_ID}`,
        }),
      });
    }
    if (url.pathname === `/v1/checks/${CHECK_ID}/stream`) {
      const last: [string, object] =
        outcome === "error"
          ? [
              "error",
              {
                type: "about:blank",
                title: "At capacity",
                status: 503,
                detail: "All model providers are busy.",
                retry_after: 30,
              },
            ]
          : ["result", result];
      return route.fulfill({
        status: 200,
        headers: { ...CORS, "content-type": "text/event-stream" },
        body: sse([
          ["step_started", step("step_started", "ledger")],
          [
            "step_done",
            step("step_done", "ledger", { summary: "no earlier check" }),
          ],
          ["step_started", step("step_started", "extract")],
          ["step_done", step("step_done", "extract", { summary: "1 claim" })],
          last,
        ]),
      });
    }
    if (url.pathname === `/v1/checks/${CHECK_ID}`) {
      return route.fulfill({
        status: 200,
        headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify({
          id: CHECK_ID,
          text: result.text,
          status: "running",
          created_at: result.created_at,
          finished_at: null,
          result: null,
          error: null,
        }),
      });
    }
    return route.fulfill({ status: 404, headers: CORS, body: "{}" });
  });
}
