import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { VerdictBadge } from "@/components/atoms/verdict-badge";
import type { GalleryItem } from "@/lib/api/client";
import { routes } from "@/lib/routes";

/** A featured check: its text (the whole card is the link) and its verdicts. */
export function GalleryCard({ item }: { item: GalleryItem }) {
  return (
    <li className="glass group hover:border-brand/50 relative flex flex-col justify-between gap-4 rounded-2xl p-5 transition hover:-translate-y-1 hover:shadow-(--shadow-lift)">
      <Link
        className="flex items-start justify-between gap-3 leading-7 font-medium after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-ring/50"
        href={routes.check(item.id)}
      >
        <span>{item.text}</span>
        <ArrowUpRight
          className="text-muted-foreground group-hover:text-brand mt-1 size-5 shrink-0 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          aria-hidden
        />
      </Link>
      <div className="flex flex-wrap gap-2">
        {item.verdicts.map((v, i) => (
          <VerdictBadge key={i} label={v} />
        ))}
      </div>
    </li>
  );
}
