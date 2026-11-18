import Link from "next/link";
import { GalleryCard } from "@/components/molecules/gallery-card";
import { NeutralityNote } from "@/components/molecules/neutrality-note";
import { TitledSection } from "@/components/molecules/titled-section";
import type { GalleryItem } from "@/lib/api/client";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** How many cards the home page shows; the Recent checks page lists them all, with filters. */
export const HOME_CARDS = 4;

/**
 * The latest checks; `items` is null when they could not be loaded, as opposed to none yet.
 * The home page shows it as "Recent checks"; a check that found HoldsUp at capacity shows it
 * under its own heading and `intro`, as something to read while the wait runs.
 */
export function Gallery({
  items,
  limit = HOME_CARDS,
  id = "gallery",
  title = strings.home.galleryHeading,
  intro,
}: {
  items: GalleryItem[] | null;
  limit?: number;
  id?: string;
  title?: string;
  intro?: string;
}) {
  return (
    <TitledSection id={id} title={title}>
      {intro && <p className="text-muted-foreground">{intro}</p>}
      <NeutralityNote />
      {items === null || items.length === 0 ? (
        <p className="glass text-muted-foreground rounded-2xl border-dashed p-6 text-center text-sm">
          {items === null
            ? strings.home.galleryUnavailable
            : strings.home.galleryEmpty}
        </p>
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2">
            {items.slice(0, limit).map((it) => (
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
