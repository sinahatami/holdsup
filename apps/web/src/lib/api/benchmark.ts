import {
  createApiClient,
  serverApiUrl,
  type Benchmark,
} from "@/lib/api/client";

/**
 * The benchmark's results, read on the server and shared by every visitor. The reports are
 * committed with the code, so they change only with a release: cached like the catalog
 * (revalidated every 15 minutes). Null when the API is down.
 */
export async function getBenchmark(): Promise<Benchmark | null> {
  "use cache";
  try {
    return await createApiClient(serverApiUrl()).benchmark();
  } catch {
    return null;
  }
}
