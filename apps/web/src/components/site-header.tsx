import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { GithubMark } from "@/components/github-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { strings } from "@/lib/strings";

export function SiteHeader() {
  return (
    <header className="glass sticky top-0 z-40 border-x-0 border-t-0 shadow-none">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-5 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-2.5 font-bold tracking-tight"
        >
          <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-xl shadow-md shadow-(color:--brand)/30">
            <ShieldCheck className="size-4.5" aria-hidden />
          </span>
          {strings.appName}
        </Link>
        <nav aria-label="Main" className="flex items-center gap-2 sm:gap-4">
          <Link
            href="/#how"
            className="text-muted-foreground hover:text-foreground hidden px-2 text-sm font-medium transition sm:block"
          >
            {strings.nav.howItWorks}
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
