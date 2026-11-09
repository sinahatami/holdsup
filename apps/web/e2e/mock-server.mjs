// A stand-in for the API, for the Next.js server rather than the browser: the browser's
// own calls are mocked inside each test (mock-api.ts), but a server-rendered page fetches
// on the server, where page.route cannot reach. It answers only what such a page reads:
// one check by id. Node runs the .ts imports as they are (it strips the types).
import { createServer } from "node:http";
import { checkResult, checkView, holdingClaim } from "../src/test/fixtures.ts";
import { CHECK_ID, DONE_ID } from "./ids.ts";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "content-type": type });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
}

const problem = (status, title) => ({ type: "about:blank", title, status });

const server = createServer((req, res) => {
  const { pathname } = new URL(req.url ?? "/", "http://localhost");
  if (pathname === "/") return send(res, 200, "ok", "text/plain");

  const match = pathname.match(/^\/v1\/checks\/([^/]+)$/);
  if (!match) return send(res, 404, problem(404, "Not found"));
  const id = match[1];

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
  // What the real API says: 422 for text that is not an id, 404 for an unknown one.
  return UUID.test(id)
    ? send(res, 404, problem(404, `No check ${id}.`))
    : send(res, 422, problem(422, "Unprocessable Entity"));
});

server.listen(Number(process.env.PORT ?? 3101), "127.0.0.1");
