import type { Page } from "@playwright/test";
import { checkResult, checkView, holdingClaim } from "../src/test/fixtures";
import { CHECK_ID } from "./ids";

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

/** What the live check ends with: the sample claim holds. */
export const result = checkResult([holdingClaim], { id: CHECK_ID });

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
        body: JSON.stringify(
          checkView({ id: CHECK_ID, status: "running", text: result.text }),
        ),
      });
    }
    return route.fulfill({ status: 404, headers: CORS, body: "{}" });
  });
}

/**
 * Mocks the browser's call that reports a wrong match. Returns the bodies it was sent, so a
 * test can check what the form posted.
 */
export async function mockReports(
  page: Page,
  outcome: "recorded" | "refused" = "recorded",
) {
  const sent: unknown[] = [];
  await page.route(`${API}/v1/checks/*/reports`, async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers: CORS });
    sent.push(req.postDataJSON());
    if (outcome === "refused") {
      return route.fulfill({
        status: 429,
        headers: { ...CORS, "content-type": "application/problem+json" },
        body: JSON.stringify({
          type: "/problems/rate-limited",
          title: "Too many reports",
          status: 429,
          detail:
            "This address has sent too many reports this hour. Please try again later.",
        }),
      });
    }
    return route.fulfill({
      status: 201,
      headers: { ...CORS, "content-type": "application/json" },
      body: JSON.stringify({ id: "44444444-4444-4444-8444-444444444444" }),
    });
  });
  return sent;
}
