import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { GalleryItem } from "@/lib/api/client";
import { VerdictBadge } from "@/components/verdict";
import { strings } from "@/lib/strings";

export function Gallery({ items }: { items: GalleryItem[] }) {
  return (
    <section aria-labelledby="gallery-heading" className="flex flex-col gap-5">
      <h2 id="gallery-heading" className="text-2xl font-bold tracking-tight">
        {strings.home.galleryHeading}
      </h2>
      {items.length === 0 ? (
        <p className="glass text-muted-foreground rounded-2xl border-dashed p-6 text-center text-sm">
          {strings.home.galleryEmpty}
        </p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {items.map((it) => (
            <li
              key={it.id}
              className="glass group hover:border-brand/50 relative flex flex-col justify-between gap-4 rounded-2xl p-5 transition hover:-translate-y-1 hover:shadow-(--shadow-lift)"
            >
              <Link
                className="flex items-start justify-between gap-3 leading-7 font-medium after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
                href={`/check/${it.id}`}
              >
                <span>{it.text}</span>
                <ArrowUpRight
                  className="text-muted-foreground group-hover:text-brand mt-1 size-5 shrink-0 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                  aria-hidden
                />
              </Link>
              <div className="flex flex-wrap gap-2">
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
