import { revalidatePath, revalidateTag } from "next/cache";
import { checkTag } from "@/lib/api/check";
import { GALLERY_TAG } from "@/lib/api/gallery";
import { routes } from "@/lib/routes";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Expire now: the next request renders again and no stale copy is served. */
const NOW = { expire: 0 };

/**
 * Drops what the site cached about a check, so its next visit reads it from the API again:
 * the API calls this when a check finishes, and the removal and claim-watch scripts after
 * they delete or update one (`?gallery=1` also drops the featured checks). It takes no
 * secret: at worst a caller makes a page render the way an uncached one does.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!UUID.test(id)) return new Response(null, { status: 404 });
  revalidateTag(checkTag(id), NOW);
  // The tag covers the cached reads; the paths cover the pages stored from them.
  for (const path of [
    routes.check(id),
    routes.checkImage(id),
    routes.embed(id),
  ]) {
    revalidatePath(path);
  }
  if (new URL(request.url).searchParams.get("gallery") === "1") {
    revalidateTag(GALLERY_TAG, NOW);
  }
  return new Response(null, { status: 204 });
}
