import { GithubMark } from "@/components/atoms/github-mark";
import { Logo } from "@/components/atoms/logo";
import { ThemeToggle } from "@/components/molecules/theme-toggle";
import Link from "next/link";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

export function SiteHeader() {
  return (
    <header className="glass sticky top-0 z-40 border-x-0 border-t-0 shadow-none">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-5 sm:px-6">
        <Logo variant="badge" />
        <nav
          aria-label={strings.nav.main}
          className="flex items-center gap-2 sm:gap-4"
        >
          <Link
            href={routes.howItWorks}
            className="text-muted-foreground hover:text-foreground hidden px-2 text-sm font-medium transition sm:block"
          >
            {strings.nav.howItWorks}
          </Link>
          <Link
            href={routes.indicators}
            className="text-muted-foreground hover:text-foreground hidden px-2 text-sm font-medium transition sm:block"
          >
            {strings.nav.canCheck}
          </Link>
          <a
            href={strings.footer.repoUrl}
            aria-label={strings.footer.github}
            className="text-muted-foreground hover:text-foreground rounded-full p-2 transition"
          >
            <GithubMark className="size-5" />
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
