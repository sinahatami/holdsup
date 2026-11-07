import Link from "next/link";
import type { GalleryItem } from "@/lib/api/client";
import { VerdictBadge } from "@/components/verdict";
import { strings } from "@/lib/strings";

export function Gallery({ items }: { items: GalleryItem[] }) {
  return (
    <section aria-labelledby="gallery-heading" className="flex flex-col gap-3">
      <h2 id="gallery-heading" className="text-xl font-semibold">
        {strings.home.galleryHeading}
      </h2>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          {strings.home.galleryEmpty}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((it) => (
            <li key={it.id} className="rounded-md border p-3">
              <Link className="underline" href={`/check/${it.id}`}>
                {it.text}
              </Link>
              <div className="mt-2 flex flex-wrap gap-2">
                {it.verdicts.map((v, i) => (
                  <VerdictBadge key={i} label={v} />
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
