import {
  createApiClient,
  serverApiUrl,
  type GalleryItem,
} from "@/lib/api/client";

const GALLERY_SIZE = 12;
/** The most the API gives in one read: the recent-checks page shows all of them. */
const RECENT_SIZE = 100;

/**
 * The featured checks, read on the server and shared by every visitor.
 *
 * Cached with the default profile (revalidated every 15 minutes), so the home
 * page is prerendered at build time and picks up a newly seeded gallery
 * without a redeploy. Empty when the API is down.
 */
export async function getGallery(): Promise<GalleryItem[]> {
  "use cache";
  try {
    return await createApiClient(serverApiUrl()).gallery(GALLERY_SIZE);
  } catch {
    return [];
  }
}

/**
 * Every featured check the API will give at once, for the recent-checks page. Cached the
 * same way; null when the API is down, so the page can tell that from "no checks yet".
 */
export async function getRecent(): Promise<GalleryItem[] | null> {
  "use cache";
  try {
    return await createApiClient(serverApiUrl()).gallery(RECENT_SIZE);
  } catch {
    return null;
  }
}
