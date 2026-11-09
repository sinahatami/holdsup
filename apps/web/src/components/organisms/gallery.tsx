import Link from "next/link";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { TitledSection } from "@/components/molecules/titled-section";
import type { GalleryItem } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

export function Gallery({ items }: { items: GalleryItem[] }) {
  return (
    <TitledSection id="gallery" title={strings.home.galleryHeading}>
      <NeutralityNote />
      {items.length === 0 ? (
        <p className="glass text-muted-foreground rounded-2xl border-dashed p-6 text-center text-sm">
          {strings.home.galleryEmpty}
        </p>
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2">
            {items.map((it) => (
              <GalleryCard key={it.id} item={it} />
            ))}
          </ul>
          <p>
            <Link
              href={routes.recent}
              className="text-brand font-medium underline underline-offset-4"
            >
              {strings.recent.seeAll}
            </Link>
          </p>
        </>
      )}
    </TitledSection>
  );
}
