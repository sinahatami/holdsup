import type { Metadata } from "next";
import Link from "next/link";
import { ExternalLink } from "@/components/atoms/external-link";
import { BackLink } from "@/components/molecules/back-link";
import { TitledSection } from "@/components/molecules/titled-section";
import { PageShell } from "@/components/templates/page-shell";
import { pageMetadata } from "@/lib/page-meta";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { pageStrings } from "@/lib/strings/pages";

const t = pageStrings.privacy;

export const metadata: Metadata = pageMetadata({
  path: routes.privacy,
  title: `${t.meta.title} · ${strings.appName}`,
  description: t.meta.description,
});

const link = "text-brand font-medium underline underline-offset-4";

/** The sections in page order, for the "On this page" links and their anchors. */
const SECTIONS = [
  ["kept", t.kept.heading],
  ["who", t.who.heading],
  ["address", t.address.heading],
  ["browser", t.browser.heading],
  ["basis", t.basis.heading],
  ["remove", t.remove.heading],
  ["terms", t.terms.heading],
  ["changes", t.changes.heading],
] as const;

const heading = Object.fromEntries(SECTIONS) as Record<
  (typeof SECTIONS)[number][0],
  string
>;

/**
 * Privacy and terms on one page: what is kept, who else handles the text, how to
 * have a check removed, and the rules for using the site. Static, so it is
 * prerendered; every statement is about what the code does today.
 */
export default function Page() {
  return (
    <PageShell>
      <BackLink />
      <div className="flex flex-col gap-3">
        <h1 className="text-4xl">{t.heading}</h1>
        <p className="text-muted-foreground text-sm">
          {t.updated.label}{" "}
          <time dateTime={t.updated.iso}>{t.updated.text}</time>
        </p>
      </div>
      <p className="text-lg leading-8">{t.intro}</p>

      <ul
        aria-label={t.glanceLabel}
        className="glass grid gap-4 rounded-2xl p-5 sm:grid-cols-2"
      >
        {t.glance.map((item) => (
          <li key={item.title} className="flex flex-col gap-1">
            <span className="font-semibold">{item.title}</span>
            <span className="text-muted-foreground text-sm leading-6">
              {item.body}
            </span>
          </li>
        ))}
      </ul>

      <nav aria-label={t.onThisPage}>
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium">
          {SECTIONS.map(([id, title]) => (
            <li key={id}>
              <a href={`#${id}`} className={link}>
                {title}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <TitledSection id="kept" title={heading.kept} className="scroll-mt-24">
        <ul className="list-disc ps-5 leading-7 marker:text-muted-foreground">
          {t.kept.items.map((item) => (
            <li key={item} className="mb-2">
              {item}
            </li>
          ))}
        </ul>
        <p className="border-brand border-s-4 ps-4 leading-7 font-medium">
          {t.kept.never}
        </p>
      </TitledSection>

      <TitledSection id="who" title={heading.who} className="scroll-mt-24">
        <p className="leading-7">{t.who.intro}</p>
        {t.who.groups.map((group) => (
          <div key={group.title} className="flex flex-col gap-3">
            <h3 className="font-semibold">{group.title}</h3>
            <p className="text-muted-foreground text-sm leading-6">
              {group.body}
            </p>
            <ul className="glass divide-y rounded-2xl">
              {group.services.map((s) => (
                <li
                  key={s.name}
                  className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3"
                >
                  <span className="flex flex-col gap-0.5">
                    <ExternalLink href={s.url}>{s.name}</ExternalLink>
                    <span className="text-muted-foreground text-sm">
                      {s.role}
                    </span>
                  </span>
                  <span className="text-sm font-medium">{s.where}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <p className="leading-7">{t.who.sources}</p>
        <p className="leading-7">{t.who.voice}</p>
      </TitledSection>

      <TitledSection
        id="address"
        title={heading.address}
        className="scroll-mt-24"
      >
        <p className="leading-7">{t.address.body}</p>
      </TitledSection>

      <TitledSection
        id="browser"
        title={heading.browser}
        className="scroll-mt-24"
      >
        <p className="leading-7">{t.browser.body}</p>
      </TitledSection>

      <TitledSection id="basis" title={heading.basis} className="scroll-mt-24">
        <p className="leading-7">{t.basis.body}</p>
      </TitledSection>

      <TitledSection
        id="remove"
        title={heading.remove}
        className="scroll-mt-24"
      >
        <ol className="flex flex-col gap-3">
          {t.remove.steps.map((step, i) => (
            <li key={step} className="glass flex gap-4 rounded-2xl p-4">
              <span
                aria-hidden
                className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
              >
                {i + 1}
              </span>
              <p className="min-w-0 self-center text-sm leading-6">{step}</p>
            </li>
          ))}
        </ol>
        <p className="leading-7">{t.remove.noClaims}</p>
        <p>
          <ExternalLink href={strings.footer.issuesUrl}>
            {t.remove.issue}
          </ExternalLink>
        </p>
        <p className="leading-7">{t.remove.authority}</p>
        <p className="text-muted-foreground leading-7">{t.remove.controller}</p>
      </TitledSection>

      <TitledSection id="terms" title={heading.terms} className="scroll-mt-24">
        <p className="leading-7">{t.terms.intro}</p>
        <ul className="list-disc ps-5 leading-7 marker:text-muted-foreground">
          {t.terms.items.map((item) => (
            <li key={item} className="mb-2">
              {item}
            </li>
          ))}
        </ul>
        <p className="flex flex-wrap gap-x-5 gap-y-2">
          <Link href={`${routes.about}#data`} className={link}>
            {t.terms.sources}
          </Link>
          <ExternalLink href={strings.footer.licenseUrl}>
            {t.terms.license}
          </ExternalLink>
        </p>
      </TitledSection>

      <TitledSection
        id="changes"
        title={heading.changes}
        className="scroll-mt-24"
      >
        <p className="leading-7">{t.changes.body}</p>
        <p>
          <ExternalLink href={t.changes.historyUrl}>
            {t.changes.history}
          </ExternalLink>
        </p>
      </TitledSection>
    </PageShell>
  );
}
