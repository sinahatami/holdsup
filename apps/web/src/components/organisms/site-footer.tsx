import Link from "next/link";
import { GithubMark } from "@/components/atoms/github-mark";
import { Logo } from "@/components/atoms/logo";
import { pill } from "@/components/atoms/pill";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const footerLink = "text-muted-foreground hover:text-foreground transition";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-5 py-12 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="flex max-w-sm flex-col gap-3">
          <Logo />
          <p className="text-muted-foreground text-sm leading-6">
            {strings.footer.blurb}
          </p>
        </div>
        <ul className="flex flex-col gap-3 text-sm font-medium">
          <li>
            <Link href={routes.home} className={footerLink}>
              {strings.nav.home}
            </Link>
          </li>
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
            <Link href={routes.about} className={footerLink}>
              {strings.nav.about}
            </Link>
          </li>
          <li>
            <a
              href={strings.footer.repoUrl}
              className={pill({ tone: "glass" })}
            >
              <GithubMark className="size-4" />
              {strings.footer.github}
            </a>
          </li>
        </ul>
      </div>
      <div className="text-muted-foreground border-t px-5 py-5 text-center text-xs">
        {strings.footer.copyright} {strings.appName} · {strings.footer.note}
      </div>
    </footer>
  );
}
