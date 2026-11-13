// A stand-in for the API, for the Next.js server rather than the browser: the browser's
// own calls are mocked inside each test (mock-api.ts), but a server-rendered page fetches
// on the server, where page.route cannot reach. It answers only what such a page reads:
// one check by id. Node runs the .ts imports as they are (it strips the types).
import { createServer } from "node:http";
import { setTimeout as sleep } from "node:timers/promises";
import {
  catalogEntry,
  checkResult,
  checkView,
  galleryClaim,
  galleryItem,
  highConfidence,
  holdingClaim,
  tolerances,
  unsureClaim,
} from "../src/test/fixtures.ts";
import { CHECK_ID, DONE_ID, RECHECK_ID, UNSURE_ID } from "./ids.ts";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "content-type": type });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
}

// Fourteen featured checks, so the list needs a second page: verdicts, places and topics
// take turns, and the quote says which is which.
const VERDICTS = ["supported", "not_supported", "partly_supported"];
const PLACES = ["IT", "FR", "DE"];
const THEMES = ["work", "health", "economy"];
const featured = Array.from({ length: 14 }, (_, i) =>
  galleryItem({
    id: `ffffffff-ffff-4fff-8fff-${String(i).padStart(12, "0")}`,
    claims: [
      galleryClaim({
        quote: `Featured claim ${i + 1}`,
        label: VERDICTS[i % 3],
        geo: PLACES[i % 3],
        theme: THEMES[i % 3],
      }),
    ],
  }),
);

// How long a stored check takes to come back (milliseconds). Zero for the e2e tests; the
// Lighthouse run sets some, because the real API is not instant and a page that streams a
// check in shows its loading frame for that long (which is when a layout shift can happen).
const CHECK_DELAY_MS = Number(process.env.CHECK_DELAY_MS ?? 0);

const problem = (status, title) => ({ type: "about:blank", title, status });

const server = createServer(async (req, res) => {
  const { pathname, searchParams } = new URL(
    req.url ?? "/",
    "http://localhost",
  );
  if (pathname === "/") return send(res, 200, "ok", "text/plain");

  if (pathname === "/v1/gallery") {
    const limit = Number(searchParams.get("limit") ?? 12);
    return send(res, 200, { items: featured.slice(0, limit) });
  }

  if (pathname === "/v1/tolerances") return send(res, 200, tolerances);

  if (pathname === "/v1/catalog") {
    return send(res, 200, {
      version: "0.7.0",
      indicators: [
        catalogEntry({
          id: "rent",
          name: "Rent prices (Eurostat)",
          theme: "prices",
          definition: "How much tenants pay for a home.",
          source_code: "prc_hicp_aind",
          aliases: ["cost of renting a home"],
          first_year: 2005,
          last_year: 2022,
        }),
        catalogEntry({
          id: "unemployment",
          name: "Unemployment rate (World Bank)",
          theme: "work",
          definition: "Share of the labour force without a job.",
          source: "the World Bank",
          source_code: "SL.UEM.TOTL.ZS",
          countries: [],
          groups: ["WORLD"],
          all_countries: true,
          first_year: 1991,
        }),
        catalogEntry({
          id: "poverty",
          name: "At-risk-of-poverty rate (Eurostat)",
          theme: "poverty",
          definition: "Share of people below 60% of the median income.",
          source_code: "ilc_li02",
          countries: ["IT", "NO"],
          first_year: 1995,
        }),
      ],
    });
  }

  const match = pathname.match(/^\/v1\/checks\/([^/]+)$/);
  if (!match) return send(res, 404, problem(404, "Not found"));
  const id = match[1];
  if (CHECK_DELAY_MS > 0) await sleep(CHECK_DELAY_MS);

  if (id === CHECK_ID) {
    return send(res, 200, checkView({ id, status: "running" }));
  }
  if (id === DONE_ID) {
    const result = checkResult([holdingClaim], { id });
    return send(
      res,
      200,
      checkView({
        id,
        status: "done",
        finished_at: result.finished_at,
        result,
      }),
    );
  }
  if (id === UNSURE_ID) {
    const result = checkResult(
      [{ ...holdingClaim, confidence: highConfidence }, unsureClaim],
      { id },
    );
    return send(
      res,
      200,
      checkView({
        id,
        status: "done",
        finished_at: result.finished_at,
        result,
      }),
    );
  }
  if (id === RECHECK_ID) {
    // DONE_ID's claim checked again with its alternative, which offers the first one back.
    const [ilo] = holdingClaim.suggestions;
    const first = holdingClaim.indicator;
    const result = checkResult(
      [
        {
          ...holdingClaim,
          indicator: { ...first, id: ilo.id, name: ilo.name },
          alternatives: [first.id],
          suggestions: [{ id: first.id, name: first.name }],
        },
      ],
      {
        id,
        text: holdingClaim.claim.quote,
        recheck_of: {
          check_id: DONE_ID,
          claim_index: 0,
          replaced: { id: first.id, name: first.name },
        },
      },
    );
    return send(
      res,
      200,
      checkView({
        id,
        status: "done",
        finished_at: result.finished_at,
        result,
      }),
    );
  }
  // What the real API says: 422 for text that is not an id, 404 for an unknown one.
  return UUID.test(id)
    ? send(res, 404, problem(404, `No check ${id}.`))
    : send(res, 422, problem(422, "Unprocessable Entity"));
});

server.listen(Number(process.env.PORT ?? 3101), "127.0.0.1");
