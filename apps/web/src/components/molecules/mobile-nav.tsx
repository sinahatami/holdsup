"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const PANEL_ID = "mobile-nav-panel";

export interface NavLink {
  href: string;
  label: string;
}

/**
 * The site's pages as a menu for screens too narrow to show them in the header
 * (below 768px). It stays open only on the page it was opened from, so
 * following a link, or the back button, closes it; Escape closes it too and
 * puts focus back on the button.
 */
export function MobileNav({ links }: { links: readonly NavLink[] }) {
  const pathname = usePathname();
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setOpenOn(null);
      button.current?.focus();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const Icon = open ? X : Menu;
  return (
    <div className="md:hidden">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={PANEL_ID}
        aria-label={open ? strings.nav.menuClose : strings.nav.menuOpen}
        onClick={() => setOpenOn(open ? null : pathname)}
        className="text-muted-foreground hover:text-foreground flex size-10 items-center justify-center rounded-full transition"
      >
        <Icon className="size-5" aria-hidden />
      </button>
      <nav
        id={PANEL_ID}
        hidden={!open}
        aria-label={strings.nav.pages}
        className="bg-background absolute inset-x-0 top-full border-b shadow-lg"
      >
        <ul className="mx-auto flex w-full max-w-5xl flex-col px-5 py-2 sm:px-6">
          {links.map(({ href, label }) => {
            const current = href === pathname;
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={current ? "page" : undefined}
                  className={cn(
                    "flex min-h-12 items-center text-base font-medium transition",
                    current
                      ? "text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
