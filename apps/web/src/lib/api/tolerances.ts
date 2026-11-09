import {
  createApiClient,
  serverApiUrl,
  type Tolerances,
} from "@/lib/api/client";

/**
 * The rules verdicts are judged by, read on the server and shared by every visitor.
 * Cached like the catalog (revalidated every 15 minutes); null when the API is down.
 */
export async function getTolerances(): Promise<Tolerances | null> {
  "use cache";
  try {
    return await createApiClient(serverApiUrl()).tolerances();
  } catch {
    return null;
  }
}
