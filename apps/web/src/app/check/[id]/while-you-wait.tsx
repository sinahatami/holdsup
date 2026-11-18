import { Gallery } from "@/components/organisms/gallery";
import { getGallery } from "@/lib/api/gallery";
import { strings } from "@/lib/strings";

/**
 * Checks done earlier, for a reader who found HoldsUp at capacity: their receipts need no
 * model, so they open while the providers are busy (the spec's "at capacity" message comes
 * "with the gallery"). The gallery read is cached, like the home page's.
 */
export async function WhileYouWait() {
  const items = await getGallery();
  const t = strings.problem.capacity;
  return (
    <Gallery
      id="while-you-wait"
      title={t.galleryHeading}
      intro={t.galleryIntro}
      items={items}
    />
  );
}
