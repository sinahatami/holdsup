import { serverApiUrl, type GalleryItem } from "@/lib/api/client";

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
    const res = await fetch(`${serverApiUrl()}/v1/gallery?limit=12`);
    if (!res.ok) return [];
    const body = (await res.json()) as { items: GalleryItem[] };
    return body.items;
  } catch {
    return [];
  }
}
