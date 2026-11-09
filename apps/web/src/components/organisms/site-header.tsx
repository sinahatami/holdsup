import { ExternalLink } from "@/components/atoms/external-link";
import { GithubMark } from "@/components/atoms/github-mark";
import { Logo } from "@/components/atoms/logo";
import { MobileNav } from "@/components/molecules/mobile-nav";
import { ThemeToggle } from "@/components/molecules/theme-toggle";
import Link from "next/link";
import { Suspense } from "react";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

// The pages shown across the header from 768px up.
const links = [
  { href: routes.indicators, label: strings.nav.canCheck },
  { href: routes.recent, label: strings.nav.recent },
  { href: routes.methodology, label: strings.nav.methodology },
];

// Below 768px they sit in a menu, together with the pages the header never lists.
const menuLinks = [...links, { href: routes.about, label: strings.nav.about }];

export function SiteHeader() {
  return (
    <header className="glass sticky top-0 z-40 border-x-0 border-t-0 shadow-none">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-5 sm:px-6">
        <Logo variant="badge" />
        <div className="flex items-center gap-2 sm:gap-4">
          <nav
            aria-label={strings.nav.main}
            className="flex items-center gap-2 sm:gap-4"
          >
            {links.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="text-muted-foreground hover:text-foreground hidden px-2 text-sm font-medium transition md:block"
              >
                {label}
              </Link>
            ))}
            <ExternalLink
              plain
              href={strings.footer.repoUrl}
              className="text-muted-foreground hover:text-foreground rounded-full p-2 transition"
            >
              <GithubMark className="size-5" />
              <span className="sr-only">{strings.footer.github}</span>
            </ExternalLink>
            <ThemeToggle />
          </nav>
          {/* It reads the page address, which a page such as a receipt only knows at request time. */}
          <Suspense fallback={<div className="size-10 md:hidden" />}>
            <MobileNav links={menuLinks} />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
