// The performance budget, in one command: `pnpm --filter @holdsup/web lighthouse`.
//
// It starts the e2e mock API (so the home page has a gallery and a finished check exists
// to open), builds the site against it, serves the production build and runs Lighthouse CI
// over the home page (lighthouserc.json) and a finished check (lighthouserc.check.json).
// Everything it starts is stopped again, pass or fail.
// The exit code is Lighthouse CI's: non-zero when a budget in either file is broken.
//
// Why two files: the home page is static, so Lighthouse's default simulated throttling
// models it well. A check page is streamed: React reveals the receipt (a Suspense
// boundary) about 300 ms after first paint, on purpose, so that the loading frame does
// not flash. Once that paint lands after the scripts have loaded, the simulation counts
// all of them as blocking, and a 0.5 s paint is reported as 3.4 s. The check page is
// therefore measured with applied (devtools) throttling, which reports what the browser
// did, and its numbers are stable run to run. Do not raise the budget to fit a model.
//
// Run it where nothing else heavy is running, and not while `next dev` is building: the
// numbers come from a throttled browser on this machine and move with its load.
import { spawn, spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const API_PORT = 3101;
const WEB_PORT = 3200;
const children = [];

function start(command, args, env) {
  const child = spawn(command, args, {
    stdio: ["ignore", "inherit", "inherit"],
    env: { ...process.env, ...env },
  });
  children.push(child);
  return child;
}

function stopAll() {
  for (const child of children) child.kill("SIGTERM");
}

async function waitFor(url) {
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // not listening yet
    }
    await sleep(500);
  }
  throw new Error(`${url} did not come up in 60 seconds`);
}

function run(command, args, env) {
  const { status } = spawnSync(command, args, {
    stdio: "inherit",
    env: { ...process.env, ...env },
  });
  return status ?? 1;
}

const siteEnv = {
  NEXT_PUBLIC_API_URL: "http://api.test",
  HOLDSUP_API_URL: `http://127.0.0.1:${API_PORT}`,
};

process.on("SIGINT", () => {
  stopAll();
  process.exit(130);
});

let code = 1;
try {
  // A small delay ensures the loading frame is on screen before the check arrives
  // (without it a fast machine may skip the frame and hide a layout shift).
  // Keep it short so the LCP budget stays tight in CI.
  start("node", ["e2e/mock-server.mjs"], {
    PORT: String(API_PORT),
    CHECK_DELAY_MS: "50",
  });
  await waitFor(`http://127.0.0.1:${API_PORT}/`);

  code = run("pnpm", ["exec", "next", "build"], siteEnv);
  if (code === 0) {
    start(
      "pnpm",
      ["exec", "next", "start", "--port", String(WEB_PORT)],
      siteEnv,
    );
    await waitFor(`http://127.0.0.1:${WEB_PORT}/`);
    // Both run, so one failure does not hide the other; the worse exit code wins.
    const extra = process.argv.slice(2);
    for (const config of ["lighthouserc.json", "lighthouserc.check.json"]) {
      const status = run("pnpm", [
        "exec",
        "lhci",
        "autorun",
        `--config=${config}`,
        ...extra,
      ]);
      code = Math.max(code, status);
    }
  }
} finally {
  stopAll();
}
process.exit(code);
