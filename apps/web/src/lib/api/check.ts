import { cache } from "react";
import {
  ApiError,
  createApiClient,
  serverApiUrl,
  type CheckView,
} from "@/lib/api/client";

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

/**
 * A check by id, read on the server. Memoized per request, so a page and its
 * metadata share one call. A finished check never changes, but a running one
 * does, so nothing here is cached across requests.
 */
export const readCheck = cache(async (id: string): Promise<CheckLookup> => {
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
});
