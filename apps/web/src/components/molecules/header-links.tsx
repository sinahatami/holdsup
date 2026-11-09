"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavLink } from "@/components/molecules/mobile-nav";
import { cn } from "@/lib/utils";

/** The pages listed across the header from 768px up, the current one marked. */
export function HeaderLinks({ links }: { links: readonly NavLink[] }) {
  const pathname = usePathname();
  return (
    <>
      {links.map(({ href, label }) => {
        const current = href === pathname;
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "hidden rounded-full px-3 py-1.5 text-sm font-medium transition md:block",
              current
                ? "bg-foreground/10 text-foreground ring-foreground/10 ring-1 ring-inset"
                : "text-muted-foreground hover:text-foreground hover:bg-foreground/5",
            )}
          >
            {label}
          </Link>
        );
      })}
    </>
  );
}
