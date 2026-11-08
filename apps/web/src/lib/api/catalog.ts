import {
  createApiClient,
  serverApiUrl,
  type CatalogResponse,
} from "@/lib/api/client";

/**
 * Everything HoldsUp can check, read on the server and shared by every visitor.
 * Cached like the gallery (revalidated every 15 minutes); null when the API is down.
 */
export async function getCatalog(): Promise<CatalogResponse | null> {
  "use cache";
  try {
    return await createApiClient(serverApiUrl()).catalog();
  } catch {
    return null;
  }
}
