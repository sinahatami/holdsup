import {
  createApiClient,
  serverApiUrl,
  type GalleryItem,
} from "@/lib/api/client";

const GALLERY_SIZE = 12;

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
