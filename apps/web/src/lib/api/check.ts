import { cacheLife, cacheTag } from "next/cache";
import { cache } from "react";
import {
  ApiError,
  createApiClient,
  serverApiUrl,
  type CheckView,
} from "@/lib/api/client";
import type { Newer } from "@/lib/watch";

/** How long the server waits for the API before it leaves the check to the browser. */
const READ_TIMEOUT_MS = 8_000;

/** The API says 404 for an id it does not know and 422 for text that is not an id. */
const MISSING = new Set([404, 422]);

/** What reading a check on the server found. */
export type CheckLookup =
  | { kind: "found"; view: CheckView }
  | { kind: "missing" }
  /** The API could not be reached or failed: the browser can still try. */
  | { kind: "unavailable" };

/** The tag on everything cached about one check, so it can be dropped at once. */
export function checkTag(id: string): string {
  return `check:${id}`;
}

/** A check that will not change again by itself: it finished or failed. */
function settled(found: CheckLookup): boolean {
  return (
    found.kind === "found" &&
    (found.view.status === "done" || found.view.status === "failed")
  );
}

/** The check as the API has it now. */
async function readFresh(id: string): Promise<CheckLookup> {
  try {
    const view = await createApiClient(serverApiUrl()).getCheck(id, {
      signal: AbortSignal.timeout(READ_TIMEOUT_MS),
    });
    return { kind: "found", view };
  } catch (err) {
    return err instanceof ApiError && MISSING.has(err.problem.status)
      ? { kind: "missing" }
      : { kind: "unavailable" };
  }
}

/**
 * The check, cached across requests. A finished or failed check is kept for a day, so its
 * page is served whole from the cache and the receipt is in the first paint; a running one,
 * or an answer from an API that is down, for seconds only, which keeps it out of a stored
 * page. What can still change a settled check (a removal, the claim watch's update) asks
 * the site to drop it (POST /api/checks/<id>/refresh), and a day is the most it can lag
 * if that request is lost.
 */
async function readCached(id: string): Promise<CheckLookup> {
  "use cache";
  cacheTag(checkTag(id));
  const found = await readFresh(id);
  if (settled(found)) cacheLife("days");
  else cacheLife("seconds");
  return found;
}

/** A check by id, read on the server. Memoized per request too, so a page and its metadata share one read. */
export const readCheck = cache(readCached);

/**
 * The newest check computed again from a finished one (`updated_by`, the claim
 * watch): its id, and its result when it can be read.
 */
export async function readNewer(id: string): Promise<Newer> {
  const found = await readCheck(id);
  return {
    id,
    result: found.kind === "found" ? (found.view.result ?? null) : null,
  };
}
