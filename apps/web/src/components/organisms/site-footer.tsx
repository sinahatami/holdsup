import Link from "next/link";
import type { ReactNode } from "react";
import { ExternalLink } from "@/components/atoms/external-link";
import { GithubMark } from "@/components/atoms/github-mark";
import { Logo } from "@/components/atoms/logo";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const footerLink =
  "text-muted-foreground hover:text-foreground block py-1 transition";

/** A short, labelled group of links; each is its own landmark for a screen reader. */
function LinkGroup({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <nav aria-label={title} className="flex flex-col gap-3">
      <p className="text-sm font-semibold" aria-hidden>
        {title}
      </p>
      <ul className="flex flex-col gap-1 text-sm font-medium">{children}</ul>
    </nav>
  );
}

/** Pages are two groups of short lists; code and licence links go to the repository. */
export function SiteFooter() {
  const t = strings.footer;
  return (
    <footer className="mt-auto border-t">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-5 py-10 sm:flex-row sm:justify-between sm:px-6">
        <div className="flex max-w-sm flex-col gap-3">
          <Logo />
          <p className="text-muted-foreground text-sm leading-6">{t.blurb}</p>
          <p className="text-muted-foreground text-sm leading-6">{t.note}</p>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:gap-16">
          <LinkGroup title={t.explore}>
            <li>
              <Link href={routes.indicators} className={footerLink}>
                {strings.nav.canCheck}
              </Link>
            </li>
            <li>
              <Link href={routes.recent} className={footerLink}>
                {strings.nav.recent}
              </Link>
            </li>
            <li>
              <Link href={routes.methodology} className={footerLink}>
                {strings.nav.methodology}
              </Link>
            </li>
            <li>
              <Link href={routes.status} className={footerLink}>
                {strings.nav.status}
              </Link>
            </li>
          </LinkGroup>
          <LinkGroup title={t.project}>
            <li>
              <Link href={routes.about} className={footerLink}>
                {strings.nav.about}
              </Link>
            </li>
            <li>
              <ExternalLink
                plain
                href={t.repoUrl}
                className={`${footerLink} flex items-center gap-2`}
              >
                <GithubMark className="size-4" />
                {t.github}
              </ExternalLink>
            </li>
            <li>
              <ExternalLink plain href={t.issuesUrl} className={footerLink}>
                {t.report}
              </ExternalLink>
            </li>
            <li>
              <ExternalLink plain href={t.licenseUrl} className={footerLink}>
                {t.license}
              </ExternalLink>
            </li>
          </LinkGroup>
        </div>
      </div>
      <div className="text-muted-foreground border-t px-5 py-4 text-center text-xs">
        {strings.appName} · {t.legal}
      </div>
    </footer>
  );
}
