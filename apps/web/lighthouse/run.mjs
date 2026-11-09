// The performance budget, in one command: `pnpm --filter @holdsup/web lighthouse`.
//
// It starts the e2e mock API (so the home page has a gallery and a finished check exists
// to open), builds the site against it, serves the production build and runs Lighthouse CI
// over the pages in lighthouserc.json. Everything it starts is stopped again, pass or fail.
// The exit code is Lighthouse CI's: non-zero when a budget in lighthouserc.json is broken.
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
  // A check takes 400 ms to come back, as from a real API, so the loading frame is on
  // screen first (without the delay a fast machine may skip it and hide a layout shift).
  start("node", ["e2e/mock-server.mjs"], {
    PORT: String(API_PORT),
    CHECK_DELAY_MS: "400",
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
    code = run("pnpm", ["exec", "lhci", "autorun", ...process.argv.slice(2)]);
  }
} finally {
  stopAll();
}
process.exit(code);
