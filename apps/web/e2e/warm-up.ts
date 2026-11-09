import type { FullConfig } from "@playwright/test";
import { DONE_ID } from "./ids";

/**
 * Compiles each page once before any test runs. A cold `next dev` takes seconds per
 * route, and tests that all arrive at once would race for the compile and time out.
 */
export default async function warmUp(config: FullConfig) {
  const base = config.projects[0].use.baseURL;
  if (!base) return;
  for (const path of [
    "/",
    "/indicators",
    "/methodology",
    "/recent",
    `/check/${DONE_ID}`,
    "/check/not-an-id",
  ]) {
    await fetch(new URL(path, base));
  }
}
