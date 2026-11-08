import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { GithubMark } from "@/components/github-mark";
import { strings } from "@/lib/strings";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-5 py-12 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="flex max-w-sm flex-col gap-3">
          <Link href="/" className="flex items-center gap-2 font-bold">
            <ShieldCheck className="text-brand size-5" aria-hidden />
            {strings.appName}
          </Link>
          <p className="text-muted-foreground text-sm leading-6">
            {strings.footer.blurb}
          </p>
        </div>
        <ul className="flex flex-col gap-3 text-sm font-medium">
          <li>
            <Link
              href="/"
              className="text-muted-foreground hover:text-foreground transition"
            >
              {strings.nav.home}
            </Link>
          </li>
          <li>
            <Link
              href="/#how"
              className="text-muted-foreground hover:text-foreground transition"
            >
              {strings.nav.howItWorks}
            </Link>
          </li>
          <li>
            <a
              href={strings.footer.repoUrl}
              className="glass hover:bg-accent inline-flex items-center gap-2 rounded-full px-4 py-2 transition"
            >
              <GithubMark className="size-4" />
              {strings.footer.github}
            </a>
          </li>
        </ul>
      </div>
      <div className="text-muted-foreground border-t px-5 py-5 text-center text-xs">
        © 2026 {strings.appName} · {strings.footer.note}
      </div>
    </footer>
  );
}
